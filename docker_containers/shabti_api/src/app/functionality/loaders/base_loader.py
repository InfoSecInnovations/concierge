from __future__ import annotations
from dataclasses import dataclass
import time
from typing import AsyncIterator, Callable, Optional


def get_current_time():
    return int(round(time.time() * 1000))


@dataclass(kw_only=True)
class ShabtiDocument:
    @dataclass(kw_only=True)
    class DocumentMetadata:
        media_type: str
        source: str
        ingest_date: int
        filename: Optional[str] = None
        languages: list[str]

    @dataclass(kw_only=True)
    class ShabtiPage:
        @dataclass(kw_only=True)
        class PageMetadata:
            page_number: Optional[int] = None
            source: Optional[str] = None

        metadata: PageMetadata
        content: str

    pages: list[ShabtiPage]
    metadata: DocumentMetadata


@dataclass(kw_only=True)
class ShabtiPageStream:
    """A document whose pages arrive over time.

    `metadata` is known before the first page, but the page count is not: a crawl discovers pages as
    it goes, so `estimated_total` is only an upper bound until the source is finished and has to be
    read again for every page rather than once up front.
    """

    metadata: ShabtiDocument.DocumentMetadata
    pages: AsyncIterator[ShabtiDocument.ShabtiPage]
    estimated_total: Callable[[], int]


def page_list_stream(
    metadata: ShabtiDocument.DocumentMetadata, pages: list[ShabtiDocument.ShabtiPage]
) -> ShabtiPageStream:
    """A stream over pages that are already all in memory, for sources that can't produce them lazily."""

    async def iterate():
        for page in pages:
            yield page

    return ShabtiPageStream(
        metadata=metadata, pages=iterate(), estimated_total=lambda: len(pages)
    )


async def collect_pages(stream: ShabtiPageStream) -> ShabtiDocument:
    """Drain a stream into a single document, for tests and anything that needs every page at once."""
    return ShabtiDocument(
        metadata=stream.metadata, pages=[page async for page in stream.pages]
    )
