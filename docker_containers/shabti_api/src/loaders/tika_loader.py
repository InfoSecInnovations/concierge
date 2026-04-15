from .base_loader import ShabtiDocument, get_current_time
from tika import parser
from bs4 import BeautifulSoup


class TikaFileLoader:
    @staticmethod
    def load(file, filename: str | None) -> ShabtiDocument:
        date_time = get_current_time()
        parsed = parser.from_buffer(file.read(), xmlContent=True)
        soup = BeautifulSoup(parsed["content"], "html.parser")
        pages = [
            {"content": page.text, "page_number": index + 1}
            for index, page in enumerate(soup.find_all("div", {"class": "page"}))
        ]
        if not len(pages):
            pages = [{"content": soup.get_text()}]
        return ShabtiDocument(
            metadata=ShabtiDocument.DocumentMetadata(
                source=filename,
                filename=filename,
                ingest_date=date_time,
                media_type=parsed["metadata"]["Content-Type"],
                languages=[parsed["metadata"]]
                if "dc:language" in parsed["metadata"]
                else [],
            ),
            pages=[
                ShabtiDocument.ShabtiPage(
                    metadata=ShabtiDocument.ShabtiPage.PageMetadata(
                        page_number=page["page_number"]
                        if "page_number" in page
                        else None
                    ),
                    content=page["content"],
                )
                for page in pages
            ],
        )
