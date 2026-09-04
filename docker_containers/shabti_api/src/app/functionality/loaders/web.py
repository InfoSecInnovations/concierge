from __future__ import annotations
import asyncio
import os
import re
from datetime import timedelta
from hashlib import blake2b
from urllib.parse import urlsplit
from uuid import uuid4
import trafilatura
from crawlee import ConcurrencySettings, service_locator
from crawlee.crawlers import (
    BasicCrawlingContext,
    BeautifulSoupCrawler,
    BeautifulSoupCrawlingContext,
)
from crawlee.errors import ServiceConflictError
from crawlee.http_clients import ImpitHttpClient
from crawlee.storage_clients import MemoryStorageClient
from crawlee.storages import RequestQueue
from shabti_types import EmptyDocumentError
from .base_loader import ShabtiDocument, ShabtiPageStream, get_current_time
from ..settings import setting
from .url_guard import check_url_allowed, same_origin

# crawlee's service locator is a global singleton, and its default storage client writes crawl state
# to ./storage on disk; a memory client has to be registered before any crawler is constructed, and
# setting a different one afterwards raises ServiceConflictError
try:
    service_locator.set_storage_client(MemoryStorageClient())
except ServiceConflictError:
    pass

HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")

DEFAULT_USER_AGENT = "ShabtiAI (+https://github.com/InfoSecInnovations/shabti)"


def extract_text(html: bytes) -> str:
    """Turn a page into plain text.

    trafilatura's main content `extract()` is deliberately not used: it is tuned for articles and
    silently mangles structured pages, keeping 16 of 250 rows on the country list test page while
    duplicating each row's data, and because that damage makes the output *longer* no length or
    coverage gate can tell it apart from a page where it merely removed chrome. `clean=True` still
    drops script, style, nav, footer, aside, form and cookie banners, which is what the bs4
    `soup.text` extractor this replaced failed to do.
    """
    return (trafilatura.html2txt(html, clean=True) or "").strip()


def scope_patterns(url: str) -> list[re.Pattern[str]]:
    """Patterns restricting a crawl to `url` and everything below it.

    The trailing slash is stripped first so `/docs` and `/docs/` scope identically, and a seed with
    a single path segment can no longer widen the crawl to the whole host.
    """
    parts = urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}"
    path = (parts.path or "/").rstrip("/")
    return [
        # crawlee matches these with re.match, so an escaped prefix is a prefix match
        re.compile(re.escape(f"{base}{path}/")),
        # the seed itself, with or without a query or fragment
        re.compile(re.escape(f"{base}{path}") + r"([?#].*)?$"),
    ]


DONE = object()


class WebLoader:
    @staticmethod
    async def stream(url: str, max_depth: int = 1) -> ShabtiPageStream:
        """Crawl `url`, handing back its pages as they are fetched.

        The crawl runs as a task of its own feeding a queue, so a consumer can embed the pages it
        already has while the crawler is still fetching the rest. Fetching is bound on remote hosts
        and embedding on the LLM host, so overlapping them costs roughly the slower of the two
        instead of their sum.

        `max_depth` of 1 fetches only `url` itself. A deeper crawl only ever goes *downwards*: it
        stays within `url`'s origin and under its path, so a caller who wants the siblings of a page
        passes its parent URL. Raises ForbiddenUrlError for URLs the server must not fetch and
        EmptyDocumentError when nothing could be extracted.
        """
        await check_url_allowed(url)
        depth = max(1, min(max_depth, setting("SHABTI_CRAWL_MAX_DEPTH")))
        max_pages = setting("SHABTI_CRAWL_MAX_PAGES")
        max_page_bytes = setting("SHABTI_CRAWL_MAX_PAGE_BYTES")
        max_total_bytes = setting("SHABTI_CRAWL_MAX_TOTAL_BYTES")
        concurrency = setting("SHABTI_CRAWL_CONCURRENCY")
        scope = scope_patterns(url)

        date_time = get_current_time()
        outbox: asyncio.Queue = asyncio.Queue()
        seen: set[bytes] = set()
        failures: list[str] = []
        total_bytes = 0
        produced = 0
        crawl_task: asyncio.Task | None = None

        async def open_crawler():
            # without a request manager of its own a crawler opens the *default* request queue, which
            # concurrent ingests in this process would share
            queue = await RequestQueue.open(alias=uuid4().hex)
            crawler = BeautifulSoupCrawler(
                request_manager=queue,
                http_client=ImpitHttpClient(
                    # no browser impersonation: identify ourselves honestly
                    browser=None,
                    headers={
                        "User-Agent": os.getenv("SHABTI_CRAWL_USER_AGENT")
                        or DEFAULT_USER_AGENT
                    },
                ),
                max_crawl_depth=depth - 1,  # crawlee counts the starting URL as depth 0
                max_requests_per_crawl=max_pages,
                respect_robots_txt_file=True,
                concurrency_settings=ConcurrencySettings(
                    max_concurrency=concurrency,
                    desired_concurrency=concurrency,
                    max_tasks_per_minute=setting("SHABTI_CRAWL_REQUESTS_PER_MINUTE"),
                ),
                navigation_timeout=timedelta(
                    seconds=setting("SHABTI_CRAWL_TIMEOUT_SECONDS")
                ),
                configure_logging=False,  # leave the API's JSON logging setup alone
                statistics_log_format="inline",
            )

            @crawler.router.default_handler
            async def handle_page(context: BeautifulSoupCrawlingContext) -> None:
                nonlocal total_bytes, produced
                # loaded_url is the URL after redirects, so this is what stops a redirect from taking
                # the crawl off the origin we checked
                loaded_url = context.request.loaded_url or context.request.url
                if not same_origin(loaded_url, url):
                    context.log.info(f"skipping {loaded_url}: redirected outside {url}")
                    return
                content_type = context.http_response.headers.get("content-type", "")
                if content_type.split(";")[0].strip().lower() not in HTML_CONTENT_TYPES:
                    context.log.info(
                        f"skipping {loaded_url}: {content_type} is not HTML"
                    )
                    return

                html = await context.http_response.read()
                # extraction is synchronous lxml work, so keep it off the event loop
                text = (await asyncio.to_thread(extract_text, html))[:max_page_bytes]
                if not text:
                    context.log.info(
                        f"skipping {loaded_url}: no text could be extracted"
                    )
                    return

                # the same page is often reachable under more than one URL, and embedding its text
                # twice would let it dominate knn results
                digest = blake2b(text.encode(), digest_size=16).digest()
                if digest in seen:
                    context.log.info(
                        f"skipping {loaded_url}: duplicate of a page already read"
                    )
                    return
                seen.add(digest)

                # handed straight to the consumer rather than collected: the queue is unbounded on
                # purpose, since the crawl already caps itself at max_pages and max_total_bytes and so
                # can never hold more than the page list this replaced. Blocking here instead would
                # eventually trip crawlee's request handler timeout and lose a page we already have.
                outbox.put_nowait(
                    ShabtiDocument.ShabtiPage(
                        metadata=ShabtiDocument.ShabtiPage.PageMetadata(
                            source=loaded_url
                        ),
                        content=text,
                    )
                )
                produced += 1
                total_bytes += len(text)
                if total_bytes >= max_total_bytes:
                    crawler.stop(
                        f"reached the {max_total_bytes} byte budget for one crawl"
                    )
                    return

                if depth > 1:
                    await context.enqueue_links(strategy="same-origin", include=scope)

            @crawler.failed_request_handler
            async def handle_failure(
                # a request that never got a response only has the basic context
                context: BasicCrawlingContext,
                error: Exception,
            ) -> None:
                failures.append(f"{context.request.url}: {error}")

            @crawler.on_skipped_request
            async def handle_skipped(request_url: str, reason: str) -> None:
                failures.append(f"{request_url}: skipped ({reason})")

            return queue, crawler

        async def run_crawl(crawler) -> None:
            try:
                # the queue is new for this crawl, so there is nothing to purge
                await crawler.run([url], purge_request_queue=False)
                outbox.put_nowait(DONE)
            except Exception as e:
                # hand the failure to the consumer so it is raised where the pages are being read,
                # rather than left on a task nobody awaits
                outbox.put_nowait(e)

        async def pages():
            nonlocal crawl_task
            # opened here rather than in stream() so a consumer that never reads the stream leaves no
            # crawlee storage behind: nothing is allocated until the first page is asked for
            queue, crawler = await open_crawler()
            crawl_task = asyncio.create_task(run_crawl(crawler))
            try:
                while True:
                    item = await outbox.get()
                    if item is DONE:
                        break
                    if isinstance(item, Exception):
                        raise item
                    yield item
            finally:
                # covers the consumer abandoning the stream part way through as well as a clean
                # finish, so an ingest failure or a disconnected client tears the crawl down
                crawl_task.cancel()
                await asyncio.gather(crawl_task, return_exceptions=True)
                await queue.drop()

            if not produced:
                # crawler.run() does not raise for individual request failures, so without this a 404
                # or a robots.txt disallow would only ever surface as "no pages"
                raise EmptyDocumentError(
                    source=url,
                    message="; ".join(failures)
                    if failures
                    else "no text could be extracted from the page",
                )

        def estimated_total() -> int:
            # the page count isn't known until the crawl ends, so this is an upper bound: every page
            # found so far, plus one for the page currently being fetched. That last term drops away
            # when the crawl finishes, which is what lets the pages still queued up behind it report
            # the true count.
            running = crawl_task is None or not crawl_task.done()
            return min(produced + (1 if running else 0), max_pages)

        return ShabtiPageStream(
            metadata=ShabtiDocument.DocumentMetadata(
                source=url,
                ingest_date=date_time,
                media_type="text/html",
                languages=[],
            ),
            pages=pages(),
            estimated_total=estimated_total,
        )
