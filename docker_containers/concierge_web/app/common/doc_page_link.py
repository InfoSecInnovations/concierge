from .md_link import md_link
from .doc_url import doc_url

def page_link(collection_name, page):
    doc_metadata = page["doc_metadata"]
    page_metadata = page["page_metadata"]
    if page["type"] == "pdf":
        return f"PDF File: {
            md_link(
                f'{doc_url(collection_name, page["type"], doc_metadata["id"])}#page={page_metadata["page"]}',
                f'page {page_metadata["page"]} of {doc_metadata["filename"]}',
            )
        }"
    if page["type"] == "web":
        return f"Web page: {md_link(page_metadata['source'])} scraped {doc_metadata['ingest_date']} from parent URL {md_link(doc_metadata['source'])}"
    if "filename" in doc_metadata:
        return f"{doc_metadata['extension']} file {
            md_link(
                doc_url(collection_name, doc_metadata['type'], doc_metadata['id']),
                doc_metadata['filename'],
            )
        }"
    return f"{doc_metadata['type']} type document from {doc_metadata['source']}"