from .base_loader import ShabtiFileLoader, ShabtiDocument, get_current_time
from langchain_unstructured.document_loaders import UnstructuredLoader
from pathlib import Path
import os
import traceback


class UnstructuredFileLoader(ShabtiFileLoader):
    @staticmethod
    def can_load(full_path: str) -> bool:
        return True

    @staticmethod
    def load(full_path: str, filename: str | None) -> ShabtiDocument:
        try:
            date_time = get_current_time()
            loader = UnstructuredLoader(file_path=full_path, strategy="fast")
            pages = loader.load()
            return ShabtiDocument(
                metadata=ShabtiFileLoader.FileMetaData(
                    type="file",
                    source=full_path,
                    filename=filename or Path(full_path).name,
                    extension=os.path.splitext(full_path)[1],
                    ingest_date=date_time,
                    media_type=pages[0].metadata["filetype"]
                    if len(pages) and "filetype" in pages[0].metadata
                    else None,
                ),
                pages=[
                    ShabtiDocument.ShabtiPage(
                        metadata=ShabtiDocument.ShabtiPage.PageMetadata(),  # TODO: use page_number from metadata, there's other good stuff in the metadata too!
                        content=page.page_content,
                    )
                    for page in pages
                ],
            )
        except Exception as e:
            traceback.print_exc()
            raise e
