from __future__ import annotations
from langchain_community.document_loaders import PyPDFLoader
import time
from loaders.base_loader import ConciergeFileLoader, ConciergeDocument
from dataclasses import dataclass
from pathlib import Path


class PDFLoader(ConciergeFileLoader):
    @dataclass
    class PDFMetadata(ConciergeDocument.DocumentMetadata):
        page: int
        filename: str

    @staticmethod
    def can_load(full_path: str) -> bool:
        return full_path.endswith(".pdf")

    @staticmethod
    def load(full_path: str) -> ConciergeDocument:
        date_time = int(round(time.time() * 1000))
        loader = PyPDFLoader(full_path)
        pages = loader.load_and_split()
        return [
            ConciergeDocument(
                metadata_type="pdf",
                metadata=PDFLoader.PDFMetadata(
                    source=full_path,
                    filename=Path(full_path).name,
                    page=page.metadata["page"] + 1,
                    ingest_date=date_time,
                ),
                content=page.page_content,
            )
            for page in pages
        ]
