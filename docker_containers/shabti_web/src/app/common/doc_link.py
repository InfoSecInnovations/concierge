from shabti_types import DocumentInfo
from .doc_url import doc_url
from .md_link import md_link
import os


def doc_link(collection_id: str, doc: DocumentInfo):
    extension = None
    if doc.media_type == "application/pdf":
        return f"PDF File: {
            md_link(doc_url(collection_id, doc.document_id), doc.filename)
        }"
    if (
        doc.media_type == "text/html" and not doc.filename
    ):  # if there's a filename then this is an uploaded HTML file rather than a web page
        return f"Web page: {md_link(doc.source)}"
    if doc.filename:
        extension = os.path.splitext(doc.filename)[1]
        return f"{extension} file {
            md_link(doc_url(collection_id, doc.document_id), doc.filename)
        }"
    return f"{extension or doc.media_type} type document from {doc.source}"
