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


def ensure_collection(client: OpenSearch, collection_name: str):
    index_name = f"{collection_name}.vectors"
    if not client.indices.exists(index_name):
        index_body = {
            "aliases": {collection_name: {"is_write_index": True}},
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
        return "long"
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
            "aliases": {collection_name: {}},
            "mappings": {
                "properties": {
                    field.name: {"type": get_field_type(field.type)}
                    for field in fields(document.metadata)
                }
            },
        }
        client.indices.create(metadata_index_name, body=index_body)
    metadata_id = client.index(metadata_index_name, vars(document.metadata))["_id"]

    total = len(document.pages)
    if not total:
        return

    page = document.pages[0]
    page_data_index_name = f"{metadata_index_name}.pages"
    if not client.indices.exists(page_data_index_name):
        index_body = {
            "aliases": {collection_name: {}},
            "mappings": {
                "properties": {
                    "parent_index": {"type": "keyword"},
                    "parent_id": {"type": "keyword"},
                    **{
                        field.name: {"type": get_field_type(field.type)}
                        for field in fields(page.metadata)
                    },
                }
            },
        }
        client.indices.create(page_data_index_name, body=index_body)

    for index, page in enumerate(document.pages):
        page_id = client.index(
            page_data_index_name,
            {
                "parent_index": metadata_index_name,
                "parent_id": metadata_id,
                **vars(page.metadata),
            },
        )["_id"]
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
                    "parent_index": page_data_index_name,
                    "parent_id": page_id,
                }
                for index, vect in enumerate(vects)
            ]
        )
        yield (index, total)
    helpers.bulk(client, entries, refresh=True)


def insert_with_tqdm(
    client: OpenSearch, collection_name: str, document: ConciergeDocument
):
    page_progress = tqdm(total=len(document.pages))
    for x in insert(client, collection_name, document):
        page_progress.n = x[0] + 1
        page_progress.refresh()
    page_progress.close()


def get_context(
    client: OpenSearch, collection_name: str, reference_limit: int, user_input: str
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
        "_source": {"includes": ["parent_index", "parent_id", "text"]},
    }

    response = client.search(body=query, index=f"{collection_name}.vectors")

    hits = [hit["_source"] for hit in response["hits"]["hits"]]

    page_metadata = {}

    for hit in hits:
        if hit["parent_index"] not in page_metadata:
            page_metadata[hit["parent_index"]] = {}
        if hit["parent_id"] not in page_metadata[hit["parent_index"]]:
            response = client.get(hit["parent_index"], hit["parent_id"])
            page_metadata[hit["parent_index"]][hit["parent_id"]] = response["_source"]

    doc_metadata = {}

    for item in page_metadata.values():
        for value in item.values():
            if value["parent_index"] not in doc_metadata:
                doc_metadata[value["parent_index"]] = {}
            if value["parent_id"] not in doc_metadata[value["parent_index"]]:
                response = client.get(value["parent_index"], value["parent_id"])
                doc_metadata[value["parent_index"]][value["parent_id"]] = response[
                    "_source"
                ]

    sources = []

    for hit in hits:
        page = page_metadata[hit["parent_index"]][hit["parent_id"]]
        doc = doc_metadata[page["parent_index"]][page["parent_id"]]
        sources.append(
            {"type": doc["type"], "page_metadata": page, "doc_metadata": doc}
        )

    return {
        "context": "\n".join([hit["text"] for hit in hits]),
        "sources": sources,
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


def delete_collection(client: OpenSearch, collection_name: str):
    indices = client.indices.resolve_index(collection_name)["aliases"][0]["indices"]
    response = client.indices.delete(index=",".join(indices))
    if not response["acknowledged"]:
        print(f"Failed to delete indices for {collection_name}")
        return False
    return True


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
