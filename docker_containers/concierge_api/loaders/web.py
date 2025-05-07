from __future__ import annotations
from loaders.base_loader import ConciergeDocLoader, ConciergeDocument, get_current_time
from dataclasses import dataclass
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from bs4 import BeautifulSoup
import re


def bs4_extractor(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return re.sub(r"\n\n+", "\n\n", soup.text).strip()


class WebLoader(ConciergeDocLoader):
    @dataclass(kw_only=True)
    class WebPageMetadata(ConciergeDocument.ConciergePage.PageMetadata):
        title: str | None
        language: str | None
        source: str

    @staticmethod
    def load(full_path: str) -> ConciergeDocument:
        date_time = get_current_time()
        loader = RecursiveUrlLoader(full_path, max_depth=50, extractor=bs4_extractor)
        pages = loader.load_and_split()
        return ConciergeDocument(
            metadata=ConciergeDocument.DocumentMetadata(
                source=full_path, ingest_date=date_time, type="web"
            ),
            pages=[
                ConciergeDocument.ConciergePage(
                    metadata=WebLoader.WebPageMetadata(
                        source=page.metadata["source"],
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
            ],
        )
