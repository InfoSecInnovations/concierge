import os
from opensearchpy import helpers
from langchain.text_splitter import RecursiveCharacterTextSplitter
from concierge_backend_lib.embeddings import create_embeddings
from loaders.base_loader import ConciergeDocument
from dataclasses import fields
from .opensearch import get_client

chunk_size = 200
chunk_overlap = 25

splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size, chunk_overlap=chunk_overlap
)


def get_field_type(python_type):
    if python_type == "int":
        return "long"
    if python_type == "float":
        return "float"
    if python_type == "bool":
        return "boolean"
    return "keyword"


def insert(
    collection_id: str,
    document: ConciergeDocument,
    binary: bytes | None = None,
):
    client = get_client()
    entries = []

    doc_index_name = f"{collection_id}.{document.metadata.type}"
    if not client.indices.exists(doc_index_name):
        index_body = {
            "aliases": {collection_id: {}},
            "mappings": {
                "properties": {
                    field.name: {"type": get_field_type(field.type)}
                    for field in fields(document.metadata)
                }
            },
        }
        client.indices.create(doc_index_name, body=index_body)
    doc_id = client.index(doc_index_name, vars(document.metadata))["_id"]

    total = len(document.pages)
    if not total:  # this shouldn't really happen
        print("document has no pages!")
        return

    if binary:
        binary_index_name = f"{collection_id}.binary"
        if not client.indices.exists(binary_index_name):
            index_body = {
                "aliases": {collection_id: {}},
                "mappings": {
                    "properties": {
                        "doc_index": {"type": "keyword"},
                        "doc_id": {"type": "keyword"},
                        "data": {"type": "binary"},
                        "media_type": {"type": "keyword"},
                    }
                },
            }
            client.indices.create(binary_index_name, index_body)
        client.index(
            binary_index_name,
            {
                "doc_index": doc_index_name,
                "doc_id": doc_id,
                "data": binary.hex(),
                "media_type": document.metadata.media_type or "text/plain",
            },
        )

    page = document.pages[0]
    page_index_name = f"{doc_index_name}.pages"
    if not client.indices.exists(page_index_name):
        index_body = {
            "aliases": {collection_id: {}},
            "mappings": {
                "properties": {
                    "doc_index": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                    **{
                        field.name: {"type": get_field_type(field.type)}
                        for field in fields(page.metadata)
                    },
                }
            },
        }
        client.indices.create(page_index_name, body=index_body)

    for index, page in enumerate(document.pages):
        page_id = client.index(
            page_index_name,
            {
                "doc_index": doc_index_name,
                "doc_id": doc_id,
                **vars(page.metadata),
            },
        )["_id"]
        chunks = splitter.split_text(page.content)
        vects = create_embeddings(chunks)
        entries.extend(
            [
                {
                    "_index": collection_id,
                    "text": chunks[index],
                    "document_vector": vect,
                    "page_index": page_index_name,
                    "page_id": page_id,
                    "doc_index": doc_index_name,
                    "doc_id": doc_id,
                }
                for index, vect in enumerate(vects)
            ]
        )
        yield (index, total, doc_id)
    helpers.bulk(client, entries, refresh=True)
