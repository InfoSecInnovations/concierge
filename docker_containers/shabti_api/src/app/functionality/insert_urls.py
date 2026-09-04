from collections.abc import AsyncGenerator

from isi_util.stream_pool import (
    PoolValue,
    StreamPool,
    StreamStoppedError,
)
from keycloak import KeycloakAuthenticationError, KeycloakPostError
from shabti_types import (
    DocumentIngestError,
    DocumentIngestInfo,
    IngestItemInfo,
    UserInfo,
)

from .ingest_events import IngestEvent, ItemFailed, ItemProgress
from .ingesting import insert_document
from .loaders.web import WebLoader


async def insert_urls(
    actor: UserInfo | None,
    collection_id: str,
    items: list[IngestItemInfo],
    max_depth: int,
    pool: StreamPool[DocumentIngestInfo],
) -> AsyncGenerator[IngestEvent, None]:
    """Crawl and ingest a batch of URLs, up to the pool's limit at a time.

    Note the crawl limits are per crawl, so this multiplies them: at the default limit of 3 that is
    up to 12 fetches in flight and 360 requests a minute outbound, possibly all at one host.
    """

    def job(item: IngestItemInfo):
        async def factory():
            # awaited inside the pool's slot rather than ahead of it, so a crawl's start-up and its
            # SSRF check don't happen for a URL that is still queued
            stream = await WebLoader.stream(item.label, max_depth)
            return insert_document(actor, collection_id, stream)

        return factory

    labels = {item.item_id: item.label for item in items}

    async with pool:
        for item in items:
            pool.submit(job(item), key=item.item_id)
        async for result in pool.results():
            if isinstance(result, PoolValue):
                yield ItemProgress(result.key, result.value)
                continue
            error = result.error
            if error is None or isinstance(error, StreamStoppedError):
                continue
            if isinstance(error, (KeycloakPostError, KeycloakAuthenticationError)):
                raise error
            # reported as it is rather than flattened the way the file route has to for back
            # compatibility: a caller wants to tell a dead link from a broken embeddings server
            yield ItemFailed(
                result.key,
                DocumentIngestError(
                    error=type(error).__name__,
                    message=getattr(error, "message", None) or str(error),
                    filename=labels.get(result.key),
                    label=labels.get(result.key),
                ),
            )
