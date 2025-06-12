from __future__ import annotations
from langchain_community.document_loaders import PyPDFLoader
from .base_loader import ShabtiFileLoader, ShabtiDocument, get_current_time
from dataclasses import dataclass
from pathlib import Path


class PDFLoader(ShabtiFileLoader):
    @dataclass(kw_only=True)
    class PDFPageMetadata(ShabtiDocument.ShabtiPage.PageMetadata):
        page: int

    @staticmethod
    def can_load(full_path: str) -> bool:
        return full_path.endswith(".pdf")

    @staticmethod
    def load(full_path: str, filename: str | None) -> ShabtiDocument:
        date_time = get_current_time()
        loader = PyPDFLoader(full_path)
        pages = loader.load_and_split()

        return ShabtiDocument(
            metadata=ShabtiFileLoader.FileMetaData(
                type="pdf",
                source=full_path,
                filename=filename or Path(full_path).name,
                ingest_date=date_time,
                media_type="application/pdf",
            ),
            pages=[
                ShabtiDocument.ShabtiPage(
                    metadata=PDFLoader.PDFPageMetadata(page=page.metadata["page"] + 1),
                    content=page.page_content,
                )
                for page in pages
            ],
        )
