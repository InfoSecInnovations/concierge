from concierge_types import DocumentInfo
from .doc_url import doc_url
from .md_link import md_link
import os

def doc_link(collection_id: str, doc: DocumentInfo):
    if doc.type == "pdf":
        return f"PDF File: {
            md_link(doc_url(collection_id, doc.type, doc.document_id), doc.filename)
        }"
    if doc.type == "web":
        return f"Web page: {md_link(doc.source)}"
    if doc.filename:
        extension = None
        if doc.filename:
            extension = os.path.splitext(doc.filename)
        return f"{extension or doc.type} file {
            md_link(doc_url(collection_id, doc.type, doc.document_id), doc.filename)
        }"
    return f"{doc.type} type document from {doc.source}"