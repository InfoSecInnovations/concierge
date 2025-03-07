from __future__ import annotations
from langchain_community.document_loaders import PyPDFLoader
from loaders.base_loader import ConciergeFileLoader, ConciergeDocument, get_current_time
from dataclasses import dataclass
from pathlib import Path


class PDFLoader(ConciergeFileLoader):
    @dataclass(kw_only=True)
    class PDFPageMetadata(ConciergeDocument.ConciergePage.PageMetadata):
        page: int

    @staticmethod
    def can_load(full_path: str) -> bool:
        return full_path.endswith(".pdf")

    @staticmethod
    def load(full_path: str) -> ConciergeDocument:
        date_time = get_current_time()
        loader = PyPDFLoader(full_path)
        pages = loader.load_and_split()

        return ConciergeDocument(
            metadata=ConciergeFileLoader.FileMetaData(
                type="pdf",
                source=full_path,
                filename=Path(full_path).name,
                ingest_date=date_time,
                media_type="application/pdf",
            ),
            pages=[
                ConciergeDocument.ConciergePage(
                    metadata=PDFLoader.PDFPageMetadata(page=page.metadata["page"] + 1),
                    content=page.page_content,
                )
                for page in pages
            ],
        )
