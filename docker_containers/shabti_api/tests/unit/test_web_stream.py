"""The crawl stream, against a throwaway HTTP server on loopback.

`check_url_allowed` is stubbed out because it rejects loopback by design, which is the whole point of
it and is covered by test_web_loader.py. Everything below the guard — the crawler, the queue, the
page handler — is the real thing.
"""

import asyncio
import threading
import time
from contextlib import aclosing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from shabti_types import EmptyDocumentError

from ...src.app.functionality.loaders import web
from ...src.app.functionality.loaders.web import WebLoader

LINKED = {
    "/": b"<html><body><h1>Index</h1><p>The index page.</p>"
    b'<a href="/a">A</a><a href="/b">B</a><a href="/c">C</a></body></html>',
    "/a": b"<html><body><p>The text of page A.</p></body></html>",
    "/b": b"<html><body><p>The text of page B.</p></body></html>",
    "/c": b"<html><body><p>The text of page C.</p></body></html>",
}

# each page links only to the next, so the crawl can only advance one request at a time
CHAIN_LENGTH = 10
CHAIN = {
    ("/" if i == 0 else f"/{i}"): (
        f"<html><body><p>The text of chain page {i}.</p>"
        f'<a href="/{i + 1}">next</a></body></html>'
    ).encode()
    for i in range(CHAIN_LENGTH)
}

BLANK = {"/": b"<html><body></body></html>"}


def serve(pages: dict[str, bytes], delay: float = 0.0):
    """Start a server for `pages`, returning it, its base URL, and when it answered each page.

    Anything not in `pages` 404s, `/robots.txt` included, which crawlee reads as allow all. Answer
    it with a 5xx instead and the whole crawl is skipped, which surfaces only as an empty document.
    """
    served: list[float] = []

    class Handler(BaseHTTPRequestHandler):
        # BaseHTTPRequestHandler requires the functions to be named do_METHOD, so we tell the linter to ignore this one.
        def do_GET(self):  # noqa: N802
            body = pages.get(self.path)
            if body is None:
                self.send_error(404)
                return
            # the seed answers at once and everything under it lags, so a consumer that gets the
            # first page before the last request is served has genuinely overlapped the two
            if delay and self.path != "/":
                time.sleep(delay)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            served.append(time.monotonic())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/", served


@pytest.fixture
def crawlable(monkeypatch):
    async def allowed(url):
        return None

    monkeypatch.setattr(web, "check_url_allowed", allowed)
    # the default of 120 would throttle a handful of requests into a multi second test
    monkeypatch.setenv("SHABTI_CRAWL_REQUESTS_PER_MINUTE", "6000")


async def test_a_crawl_hands_over_pages_as_it_finds_them(crawlable):
    server, url, served = serve(LINKED, delay=0.4)
    try:
        stream = await WebLoader.stream(url, max_depth=2)
        first_page_at = None
        contents = []
        async with aclosing(stream.pages) as pages:
            async for page in pages:
                if first_page_at is None:
                    first_page_at = time.monotonic()
                contents.append(page.content)
    finally:
        server.shutdown()

    assert len(contents) == 4
    # the point of the whole change: the caller had a page in hand while the crawler was still
    # fetching the rest, instead of waiting for the crawl to finish
    assert first_page_at < max(served)


async def test_the_total_climbs_and_ends_exact(crawlable):
    server, url, served = serve(LINKED)
    try:
        stream = await WebLoader.stream(url, max_depth=2)
        while_crawling = []
        seen = 0
        async with aclosing(stream.pages) as pages:
            async for _ in pages:
                seen += 1
                while_crawling.append(stream.estimated_total())
                # a progress bar can't be asked to show more than its maximum
                assert while_crawling[-1] >= seen
        # once the crawl is over the count stops being a guess. `insert` reports its last page after
        # the loop has ended for exactly this reason, so the final progress item carries a real total
        when_finished = stream.estimated_total()
    finally:
        server.shutdown()

    assert seen == 4
    assert while_crawling == sorted(
        while_crawling
    ), "the estimate has to climb, not wander"
    # the estimate carries a spare page for the one that might still be in flight, and gives it back
    # at the end, which is what lands the progress bar on 100% rather than one short
    assert max(while_crawling) == 5
    assert when_finished == 4


async def test_the_total_never_exceeds_the_page_cap(crawlable, monkeypatch):
    monkeypatch.setenv("SHABTI_CRAWL_MAX_PAGES", "3")
    server, url, served = serve(CHAIN)
    try:
        stream = await WebLoader.stream(url, max_depth=CHAIN_LENGTH)
        seen = 0
        async with aclosing(stream.pages) as pages:
            async for _ in pages:
                seen += 1
                assert stream.estimated_total() <= 3
    finally:
        server.shutdown()

    assert seen == 3


async def test_a_crawl_that_finds_no_text_is_empty(crawlable):
    server, url, served = serve(BLANK)
    try:
        stream = await WebLoader.stream(url)
        with pytest.raises(EmptyDocumentError) as raised:
            async with aclosing(stream.pages) as pages:
                async for _ in pages:
                    pass
    finally:
        server.shutdown()

    assert raised.value.source == url


async def test_abandoning_the_stream_stops_the_crawl(crawlable):
    # a chain rather than a fan out, so a crawl that kept running would keep making requests we can
    # count rather than finishing the lot concurrently before we could look
    server, url, served = serve(CHAIN, delay=0.2)
    try:
        stream = await WebLoader.stream(url, max_depth=CHAIN_LENGTH)
        async with aclosing(stream.pages) as pages:
            async for _ in pages:
                break
        await asyncio.sleep(1.0)
        # left running, the chain would have been most of the way through by now
        assert len(served) < CHAIN_LENGTH // 2
    finally:
        server.shutdown()
