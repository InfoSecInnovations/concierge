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
        type: str
        source: str
        ingest_date: int

    @dataclass(kw_only=True)
    class ShabtiPage:
        @dataclass(kw_only=True)
        class PageMetadata:
            pass

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


class ShabtiFileLoader(ShabtiDocLoader):
    @dataclass(kw_only=True)
    class FileMetaData(ShabtiDocument.DocumentMetadata):
        filename: str
        media_type: str | None = None

    @staticmethod
    @abstractmethod
    def can_load(full_path: str) -> bool:
        # check if this loader can load the file
        pass
