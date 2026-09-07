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


def container_value(metadata, key: str):
    """One metadata value as the container itself reported it.

    `/rmeta/xml` answers with an entry per embedded resource as well as one for the container, and
    tika-python merges them into a single dict, promoting every key more than one entry carries to a
    list. So a zip's - or a docx-with-an-image's - `Content-Type` arrives as
    `["application/zip", "text/plain", ...]` rather than the string the rest of the stack is typed
    for, which used to reach `DocumentIngestInfo.document_type` and fail validation there. The
    container is the first entry, so its own value is the first element.
    """
    value = metadata.get(key)
    return value[0] if isinstance(value, list) else value


def get_languages(metadata) -> list[str]:
    """Every language the container declares, without what the merge above adds.

    Tika reports this as a bare string for most formats and a list where a document declares more
    than one, and merging appends one entry per embedded resource - each usually repeating its
    container's language, and each possibly a list of its own, so the result can be nested.
    Flattened and deduplicated rather than truncated to the first: a genuinely multilingual document
    and a merged one are indistinguishable by this point, and dropping duplicates is right for both.
    """
    language = metadata.get("dc:language")
    if not language:
        return []
    values = language if isinstance(language, list) else [language]
    flattened = [
        item
        for value in values
        for item in (value if isinstance(value, list) else [value])
        if item
    ]
    # `dict.fromkeys` rather than a set: the container's own language should stay first
    return list(dict.fromkeys(flattened))


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
                # never None: `DocumentIngestInfo.document_type` is a required str, and Tika
                # omits the header for a format it could not identify at all
                media_type=container_value(parsed["metadata"], "Content-Type")
                or "application/octet-stream",
                languages=get_languages(parsed["metadata"]),
            ),
            # tika-python leaves this None when Tika extracted no text at all, which used to
            # be a TypeError in the parse and so a load failure. Empty is the truth: the
            # caller reports an empty document rather than one that could not be read
            extract_pages(parsed["content"] or ""),
        )
