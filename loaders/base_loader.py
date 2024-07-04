from __future__ import annotations
from dataclasses import dataclass
from abc import ABCMeta, abstractmethod
import time


def get_current_time():
    return int(round(time.time() * 1000))


@dataclass
class ConciergeDocument:
    @dataclass
    class DocumentMetadata:
        type: str
        source: str
        ingest_date: int

    @dataclass
    class ConciergePage:
        @dataclass
        class ConciergePageMetadata:
            pass

        metadata: ConciergePageMetadata
        content: str

    pages: list[ConciergePage]
    metadata: DocumentMetadata


class ConciergeDocLoader(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def load(full_path: str) -> ConciergeDocument:
        # load pages
        pass


class ConciergeFileLoader(ConciergeDocLoader):
    @dataclass
    class FileMetaData(ConciergeDocument.DocumentMetadata):
        filename: str

    @staticmethod
    @abstractmethod
    def can_load(full_path: str) -> bool:
        # check if this loader can load the file
        pass
