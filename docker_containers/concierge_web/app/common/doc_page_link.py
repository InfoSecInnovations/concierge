from .md_link import md_link
from .doc_url import doc_url
from typing import Any
from datetime import datetime


def page_link(collection_id: str, page: dict[str, Any]):
    doc_metadata = page["doc_metadata"]
    page_metadata = page["page_metadata"]
    if page["type"] == "pdf":
        return f"PDF File: {
            md_link(
                f'{doc_url(collection_id, page["type"], doc_metadata["id"])}#page={page_metadata["page"]}',
                f'page {page_metadata["page"]} of {doc_metadata["filename"]}',
            )
        }"
    if page["type"] == "web":
        # we store the timestamp in ms but Python uses s timestamps
        ingest_time = datetime.fromtimestamp(doc_metadata["ingest_date"] / 1000)
        return f"Web page: {md_link(page_metadata['source'])} scraped {ingest_time.ctime()} from parent URL {md_link(doc_metadata['source'])}"
    if "filename" in doc_metadata:
        return f"{doc_metadata['extension']} file {
            md_link(
                doc_url(collection_id, doc_metadata['type'], doc_metadata['id']),
                doc_metadata['filename'],
            )
        }"
    return f"{doc_metadata['type']} type document from {doc_metadata['source']}"
