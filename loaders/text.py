from __future__ import annotations
from langchain_community.document_loaders import TextLoader
from binaryornot.check import is_binary
import os
from loaders.base_loader import ConciergeFileLoader, ConciergeDocument, get_current_time
from dataclasses import dataclass
from pathlib import Path


class TextFileLoader(ConciergeFileLoader):
    @dataclass
    class TextFileMetadata(ConciergeFileLoader.FileMetaData):
        extension: str

    @staticmethod
    def can_load(full_path: str) -> bool:
        return not is_binary(full_path)

    @staticmethod
    def load(full_path: str) -> ConciergeDocument:
        date_time = get_current_time()
        loader = TextLoader(full_path)
        pages = loader.load()
        return [
            ConciergeDocument(
                metadata_type="plaintext",
                metadata=TextFileLoader.TextFileMetadata(
                    source=full_path,
                    filename=Path(full_path).name,
                    extension=os.path.splitext(full_path)[1],
                    ingest_date=date_time,
                ),
                content=page.page_content,
            )
            for page in pages
        ]
