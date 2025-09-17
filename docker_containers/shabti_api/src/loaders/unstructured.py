from .base_loader import ShabtiDocument, get_current_time
from langchain_unstructured.document_loaders import UnstructuredLoader


class UnstructuredFileLoader:
    @staticmethod
    def load(file, filename: str | None) -> ShabtiDocument:
        date_time = get_current_time()
        loader = UnstructuredLoader(
            file=file,
            strategy="auto",
            chunking_strategy="by_title",
            metadata_filename=filename,
        )
        pages = loader.load()
        if not len(pages):
            print("The document had no pages!")
            return None
        print(pages[0].metadata)
        return ShabtiDocument(
            metadata=ShabtiDocument.DocumentMetadata(
                source=filename,
                filename=filename,
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
