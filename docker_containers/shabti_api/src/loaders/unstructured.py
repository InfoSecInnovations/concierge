from .base_loader import ShabtiDocLoader, ShabtiDocument, get_current_time
from langchain_unstructured.document_loaders import UnstructuredLoader
from pathlib import Path


class UnstructuredFileLoader(ShabtiDocLoader):
    @staticmethod
    def load(full_path: str, filename: str | None) -> ShabtiDocument:
        date_time = get_current_time()
        loader = UnstructuredLoader(
            file_path=full_path, strategy="auto", chunking_strategy="by_title"
        )
        pages = loader.load()
        if not len(pages):
            return None
        print(pages[0].metadata)
        return ShabtiDocument(
            metadata=ShabtiDocument.DocumentMetadata(
                source=full_path,
                filename=filename or Path(full_path).name,
                ingest_date=date_time,
                media_type=pages[0].metadata["filetype"],
                languages=pages[0].metadata["languages"],
            ),
            pages=[
                ShabtiDocument.ShabtiPage(
                    metadata=ShabtiDocument.ShabtiPage.PageMetadata(
                        page_number=page.metadata["page_number"]
                        if "page_number" in page.metadata
                        else None
                    ),
                    content=page.page_content,
                )
                for page in pages
            ],
        )
