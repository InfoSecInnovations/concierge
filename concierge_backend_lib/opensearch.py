import os
from dotenv import load_dotenv
from opensearchpy import OpenSearch, helpers
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm
from concierge_backend_lib.embeddings import create_embeddings
from loaders.base_loader import ConciergeDocument
from dataclasses import fields

load_dotenv()
HOST = os.getenv("OPENSEARCH_HOST") or "localhost"

chunk_size = 200
chunk_overlap = 25

splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size, chunk_overlap=chunk_overlap
)


def get_client():
    host = HOST
    port = 9200

    return OpenSearch(hosts=[{"host": host, "port": port}], use_ssl=False)


def ensure_index(client: OpenSearch, index_name: str):
    if not client.indices.exists(index_name):
        index_body = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "document_vector": {
                        "type": "knn_vector",
                        "dimension": 384,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "lucene",
                            "parameters": {},
                        },
                    },
                    "parent_index": {"type": "keyword"},
                    "parent_id": {"type": "keyword"},
                }
            },
        }
        client.indices.create(index_name, body=index_body)


def get_field_type(python_type):
    if python_type == "int":
        return "integer"
    if python_type == "float":
        return "float"
    if python_type == "bool":
        return "boolean"
    return "keyword"


def insert(client: OpenSearch, collection_name: str, document: ConciergeDocument):
    entries = []

    metadata_index_name = f"{collection_name}.{document.metadata.type}"
    if not client.indices.exists(metadata_index_name):
        index_body = {
            "mappings": {
                "properties": {
                    "collection": {"type": "keyword"},
                    **{
                        field.name: {"type": get_field_type(field.type)}
                        for field in fields(document.metadata)
                    },
                }
            }
        }
        print(index_body)
        client.indices.create(metadata_index_name, body=index_body)
    # TODO: insert document and get ID

    total = len(document.pages)

    for index, page in enumerate(document.pages):
        # TODO: ensure index using metadata type + pages
        # TODO: insert page and get ID
        chunks = splitter.split_text(page.content)
        vects = create_embeddings(chunks)
        entries.extend(
            [
                {
                    "_index": collection_name,
                    "text": chunks[index],
                    "document_vector": vect,
                }
                for index, vect in enumerate(vects)
            ]
        )
        yield (index, total)
    helpers.bulk(client, entries, refresh=True)


# def insert(client: OpenSearch, index_name: str, pages: list[ConciergeDocument]):
#     entries = []
#     total = len(pages)

#     for index, page in enumerate(pages):
#         chunks = splitter.split_text(page.content)
#         vects = create_embeddings(chunks)
#         entries.extend(
#             [
#                 {
#                     "_index": index_name,
#                     "metadata_type": page.metadata_type,
#                     "metadata": jsons.dump(page.metadata),
#                     "text": chunks[index],
#                     "document_vector": vect,
#                 }
#                 for index, vect in enumerate(vects)
#             ]
#         )
#         yield (index, total)
#     helpers.bulk(client, entries, refresh=True)


def insert_with_tqdm(
    client: OpenSearch, index_name: str, pages: list[ConciergeDocument]
):
    page_progress = tqdm(total=len(pages))
    for x in insert(client, index_name, pages):
        page_progress.n = x[0] + 1
        page_progress.refresh()
    page_progress.close()


def get_context(
    client: OpenSearch, index_name: str, reference_limit: int, user_input: str
):
    query = {
        "size": reference_limit,
        "query": {
            "knn": {
                "document_vector": {
                    "vector": create_embeddings(user_input),
                    "min_score": 0.8,  # this is quite a magic number, tweak as needed!
                }
            }
        },
        "_source": {"includes": ["metadata_type", "metadata", "text"]},
    }

    response = client.search(body=query, index=index_name)

    hits = [hit["_source"] for hit in response["hits"]["hits"]]

    return {
        "context": "\n".join([hit["text"] for hit in hits]),
        "sources": [
            {"type": hit["metadata_type"], "metadata": hit["metadata"]} for hit in hits
        ],
    }


def get_indices(client: OpenSearch):
    response = client.indices.get("*")
    # TODO: we must be able to do this in OpenSearch somehow?
    response = {
        k: v
        for k, v in response.items()
        if "document_vector" in v["mappings"]["properties"]
        and v["mappings"]["properties"]["document_vector"]["type"] == "knn_vector"
    }
    return list(response.keys())


def delete_index(client: OpenSearch, index_name: str):
    response = client.indices.delete(index=index_name)
    return response["acknowledged"]


def get_documents(client: OpenSearch, index_name: str):
    query = {
        "size": 0,
        "aggs": {
            "documents": {
                "multi_terms": {
                    "size": 100000,
                    "terms": [
                        {"field": "metadata_type"},
                        {
                            "field": "metadata.source",
                        },
                        {"field": "metadata.extension", "missing": "n/a"},
                    ],
                }
            }
        },
    }

    response = client.search(body=query, index=index_name)

    return [
        {
            "type": bucket["key"][0],
            "source": bucket["key"][1],
            "extension": bucket["key"][2],
            "vector_count": bucket["doc_count"],
        }
        for bucket in response["aggregations"]["documents"]["buckets"]
    ]


def delete_document(client: OpenSearch, index_name: str, type: str, source: str):
    query = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"metadata_type": type}},
                    {"term": {"metadata.source": source}},
                ]
            }
        }
    }
    response = client.delete_by_query(body=query, index=index_name, refresh=True)

    return response["deleted"]
