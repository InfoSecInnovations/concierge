import os
from dotenv import load_dotenv
from opensearchpy import OpenSearch

load_dotenv()
HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_ADMIN_PASSWORD = os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD")


def get_client():
    host = HOST
    port = 9200

    if OPENSEARCH_ADMIN_PASSWORD:
        return OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=("admin", OPENSEARCH_ADMIN_PASSWORD),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False,
        )

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
                    "page_index": {"type": "keyword"},
                    "page_id": {"type": "keyword"},
                    "doc_index": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                }
            },
        }
        print(f"creating {collection_name}")
        try:
            client.indices.create(index_name, body=index_body)
        except Exception as e:
            print(f"[ERROR]: {e}")


def get_collections(client: OpenSearch, index_pattern="*"):
    try:
        response = client.indices.get(index_pattern, allow_no_indices=True)
        # TODO: can we do this in OpenSearch somehow?
        response = [
            list(index["aliases"].keys())[0]
            for index in response.values()
            if "document_vector" in index["mappings"]["properties"]
            and index["mappings"]["properties"]["document_vector"]["type"]
            == "knn_vector"
        ]
        return response
    except Exception as e:
        print(f"[ERROR]: {e}")
        return []


def delete_collection(client: OpenSearch, collection_name: str):
    # get all indices in alias
    indices = client.indices.resolve_index(collection_name)["aliases"][0]["indices"]
    # deleting all indices also removes the alias
    response = client.indices.delete(index=",".join(indices))
    if not response["acknowledged"]:
        print(f"Failed to delete indices for {collection_name}")
        return False
    return True


def get_documents(client: OpenSearch, collection_name: str):
    # get all indices in alias
    indices = client.indices.resolve_index(collection_name)["aliases"][0]["indices"]
    # locate top level indices in collection alias
    mappings = client.indices.get_mapping(",".join(indices))
    top_level = [
        index
        for index in indices
        if "doc_index" not in mappings[index]["mappings"]["properties"]
    ]
    # if there aren't any document indices we want to return here to avoid querying all existing data
    if not top_level:
        return []
    # get documents from all of these
    query = {
        "size": 10000,  # this is the maximum number of results
        "query": {"match_all": {}},
    }
    response = client.search(body=query, index=",".join(top_level))
    docs = [
        {**hit["_source"], "id": hit["_id"], "index": hit["_index"]}
        for hit in response["hits"]["hits"]
    ]
    for doc in docs:
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"doc_id": doc["id"]}},
                        {"term": {"doc_index": doc["index"]}},
                    ],
                    "must_not": {
                        "exists": {
                            "field": "document_vector"
                        }  # if there's no vector field this is a page
                    },
                }
            }
        }
        doc["page_count"] = client.count(body=query, index=collection_name)["count"]
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"doc_id": doc["id"]}},
                        {"term": {"doc_index": doc["index"]}},
                    ],
                    "must": {
                        "exists": {
                            "field": "document_vector"
                        }  # we want vectors only here
                    },
                }
            }
        }
        doc["vector_count"] = client.count(body=query, index=collection_name)["count"]

    return docs


def delete_document(
    client: OpenSearch, collection_name: str, doc_type: str, doc_id: str
):
    doc_index = f"{collection_name}.{doc_type}"
    query = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"doc_id": doc_id}},
                    {"term": {"doc_index": doc_index}},
                ]
            }
        }
    }
    response = client.delete_by_query(body=query, index=collection_name)
    deleted_count = response["deleted"]
    client.delete(doc_index, doc_id, refresh=True)
    return deleted_count + 1
