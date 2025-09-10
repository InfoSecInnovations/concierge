from __future__ import annotations
from .base_loader import ShabtiDocLoader, ShabtiDocument, get_current_time
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from bs4 import BeautifulSoup
import re


def bs4_extractor(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return re.sub(r"\n\n+", "\n\n", soup.text).strip()


class WebLoader(ShabtiDocLoader):
    @staticmethod
    def load(full_path: str) -> ShabtiDocument | None:
        date_time = get_current_time()
        loader = RecursiveUrlLoader(full_path, max_depth=50, extractor=bs4_extractor)
        pages = loader.load_and_split()
        if not len(pages):
            return None
        return ShabtiDocument(
            metadata=ShabtiDocument.DocumentMetadata(
                source=full_path,
                ingest_date=date_time,
                media_type="text/html",
                languages=[pages[0].metadata["language"]]
                if "language" in pages[0].metadata
                else [],
            ),
            pages=[
                ShabtiDocument.ShabtiPage(
                    metadata=ShabtiDocument.ShabtiPage.PageMetadata(
                        source=page.metadata["source"]
                    ),
                    content=page.page_content,
                )
                for page in pages
            ],
        )
