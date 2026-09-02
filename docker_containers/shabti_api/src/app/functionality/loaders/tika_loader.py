from .base_loader import (
    ShabtiDocument,
    ShabtiPageStream,
    get_current_time,
    page_list_stream,
)
from tika import parser
from lxml import etree


def extract_pages(xhtml: str) -> list[ShabtiDocument.ShabtiPage]:
    """Pull the page divs out of Tika's XHTML.

    lxml's pull parser rather than BeautifulSoup: on a 2000 page PDF `html.parser` spent longer on
    this than the Tika server spent producing the document in the first place, and built a tree
    several times the size. Emitted elements are dropped as we go, which is what keeps the parse flat
    in memory, so that can only happen on the page branch: a document with no page divs at all needs
    the whole tree intact for the fallback below.
    """
    pull_parser = etree.HTMLPullParser(events=("end",), no_network=True, recover=True)
    pages: list[ShabtiDocument.ShabtiPage] = []

    def drain():
        for _, element in pull_parser.read_events():
            if element.tag != "div" or element.get("class") != "page":
                continue
            pages.append(
                ShabtiDocument.ShabtiPage(
                    metadata=ShabtiDocument.ShabtiPage.PageMetadata(
                        page_number=len(pages) + 1
                    ),
                    content="".join(element.itertext()),
                )
            )
            element.clear()
            previous = element.getprevious()
            while previous is not None:
                element.getparent().remove(previous)
                previous = element.getprevious()

    pull_parser.feed(xhtml)
    drain()
    root = pull_parser.close()
    drain()
    if pages:
        return pages

    # formats that aren't paginated (plain text, word processor documents) produce no page divs at
    # all, and become a single page holding the whole body
    text = "".join(root.itertext()) if root is not None else ""
    if not text.strip():
        return []
    return [
        ShabtiDocument.ShabtiPage(
            metadata=ShabtiDocument.ShabtiPage.PageMetadata(), content=text
        )
    ]


def get_languages(metadata) -> list[str]:
    # Tika reports this as a bare string for most formats and a list where a document declares more
    # than one
    language = metadata.get("dc:language")
    if not language:
        return []
    return list(language) if isinstance(language, list) else [language]


class TikaFileLoader:
    @staticmethod
    def load(file, filename: str | None) -> ShabtiPageStream:
        date_time = get_current_time()
        parsed = parser.from_buffer(
            file.read(),
            xmlContent=True,
            requestOptions={"timeout": None},
            headers={
                "X-Tika-PDFOcrStrategy": "no_ocr"
            },  # at the moment we're not using OCR at all as it can be very slow
        )
        return page_list_stream(
            ShabtiDocument.DocumentMetadata(
                source=filename,
                filename=filename,
                ingest_date=date_time,
                media_type=parsed["metadata"]["Content-Type"],
                languages=get_languages(parsed["metadata"]),
            ),
            extract_pages(parsed["content"]),
        )
