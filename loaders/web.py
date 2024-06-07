from __future__ import annotations
from loaders.base_loader import ConciergeDocLoader, ConciergeDocument, get_current_time
from dataclasses import dataclass
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader


@dataclass
class WebMetadata(ConciergeDocument.DocumentMetadata):
    title: str | None
    language: str | None


class WebLoader(ConciergeDocLoader):
    @staticmethod
    def load(full_path: str) -> list[ConciergeDocument]:
        date_time = get_current_time()
        loader = RecursiveUrlLoader(full_path, max_depth=100)
        pages = loader.load_and_split()
        return [
            ConciergeDocument(
                metadata_type="web",
                metadata=WebMetadata(
                    source=full_path,
                    ingest_date=date_time,
                    title=None
                    if "title" not in page.metadata
                    else page.metadata["title"],
                    language=None
                    if "language" not in page.metadata
                    else page.metadata["language"],
                ),
                content=page.page_content,
            )
            for page in pages
        ]
