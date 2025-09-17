from __future__ import annotations
from dataclasses import dataclass
import time
from typing import Optional


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
