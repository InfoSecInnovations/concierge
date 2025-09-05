from __future__ import annotations
from dataclasses import dataclass
from abc import ABCMeta, abstractmethod
import time


def get_current_time():
    return int(round(time.time() * 1000))


@dataclass(kw_only=True)
class ShabtiDocument:
    @dataclass(kw_only=True)
    class DocumentMetadata:
        media_type: str
        source: str
        ingest_date: int
        filename: str | None
        language: str

    @dataclass(kw_only=True)
    class ShabtiPage:
        @dataclass(kw_only=True)
        class PageMetadata:
            page_number: int | None
            source: str | None

        metadata: PageMetadata
        content: str

    pages: list[ShabtiPage]
    metadata: DocumentMetadata


class ShabtiDocLoader(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def load(full_path: str, filename: str | None) -> ShabtiDocument:
        # load pages
        pass
