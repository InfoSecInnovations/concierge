from __future__ import annotations
from langchain_community.document_loaders import TextLoader
from binaryornot.check import is_binary
import os
from .base_loader import ShabtiFileLoader, ShabtiDocument, get_current_time
from pathlib import Path


class TextFileLoader(ShabtiFileLoader):
    @staticmethod
    def can_load(full_path: str) -> bool:
        return not is_binary(full_path)

    @staticmethod
    def load(full_path: str, filename: str | None) -> ShabtiDocument:
        date_time = get_current_time()
        loader = TextLoader(full_path, autodetect_encoding=True)
        pages = loader.load()
        return ShabtiDocument(
            metadata=ShabtiFileLoader.FileMetaData(
                source=full_path,
                filename=filename or Path(full_path).name,
                extension=os.path.splitext(full_path)[1],
                ingest_date=date_time,
                type="plaintext",
            ),
            pages=[  # we just load the whole file into a single sub document
                ShabtiDocument.ShabtiPage(
                    metadata=ShabtiDocument.ShabtiPage.PageMetadata(),
                    content=page.page_content,
                )
                for page in pages
            ],
        )
