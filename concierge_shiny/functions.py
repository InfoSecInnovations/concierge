import ntpath


def chunk_link(uploads_dir, chunk):
    metadata = chunk["metadata"]
    if chunk["type"] == "pdf":
        return f'PDF File: [page {metadata["page"]} of {metadata["filename"]}](<{uploads_dir}/{metadata["filename"]}#page={metadata["page"]}>){{target="_blank"}}'
    if chunk["type"] == "web":
        return f'Web page: <{metadata["source"]}>{{target="_blank"}} scraped {metadata["ingest_date"]}'


def doc_link(uploads_dir, doc):
    if doc["type"] == "pdf":
        filename = ntpath.basename(doc["source"])
        return f'PDF File: [{filename}](<{uploads_dir}/{filename}>){{target="_blank"}}'
    if doc["type"] == "web":
        return f'Web page: <{doc["source"]}>{{target="_blank"}}'
