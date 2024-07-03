from __future__ import annotations
from langchain_community.document_loaders import PyPDFLoader
from loaders.base_loader import ConciergeFileLoader, ConciergeDocument, get_current_time
from dataclasses import dataclass
from pathlib import Path


class PDFLoader(ConciergeFileLoader):
    @dataclass
    class PDFPageMetadata(ConciergeDocument.SubDocument.SubDocumentMetadata):
        page: int

    @staticmethod
    def can_load(full_path: str) -> bool:
        return full_path.endswith(".pdf")

    @staticmethod
    def load(full_path: str) -> ConciergeDocument:
        date_time = get_current_time()
        loader = PyPDFLoader(full_path)
        pages = loader.load_and_split()
        sub_docs = {}
        for page in pages:
            if page.metadata["page"] + 1 not in sub_docs:
                sub_docs[page.metadata["page"] + 1] = ConciergeDocument.SubDocument(
                    metadata=PDFLoader.PDFPageMetadata(page=page.metadata["page"] + 1),
                    chunks=[],
                )
            sub_docs[page.metadata["page"] + 1].chunks.append(page.page_content)

        return ConciergeDocument(
            metadata_type="pdf",
            metadata=ConciergeDocument.DocumentMetadata(
                source=full_path,
                filename=Path(full_path).name,
                ingest_date=date_time,
                sub_docs=sub_docs.values(),
            ),
        )
