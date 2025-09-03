import os
from opensearchpy import OpenSearch


MAPPING_INDEX_NAME = "collection_mappings"
FILES_INDEX_NAME = "file_mappings"


def get_client():
    port = 9200
    return OpenSearch(
        hosts=[{"host": os.getenv("OPENSEARCH_HOST", "localhost"), "port": port}],
        use_ssl=False,
    )


def create_collection_index(collection_id):
    client = get_client()
    index_name = f"{collection_id}.vectors"
    index_body = {
        "aliases": {collection_id: {"is_write_index": True}},
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "document_vector": {
                    "type": "knn_vector",
                    "dimension": 768,
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
                "doc_lookup_id": {"type": "keyword"},
            }
        },
    }
    client.indices.create(index=index_name, body=index_body)
    document_ids_index = f"{collection_id}.document_lookup"
    document_ids_body = {
        "aliases": {collection_id: {}},
        "mappings": {
            "properties": {
                "doc_index": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
            }
        },
    }
    client.indices.create(index=document_ids_index, body=document_ids_body)


def create_index_mapping(collection_id, collection_name):
    client = get_client()
    if not client.indices.exists(index=MAPPING_INDEX_NAME):
        index_body = {
            "mappings": {"properties": {"collection_name": {"type": "keyword"}}}
        }
        client.indices.create(index=MAPPING_INDEX_NAME, body=index_body)
    client.index(
        index=MAPPING_INDEX_NAME,
        body={"collection_name": collection_name},
        id=collection_id,
        refresh=True,
    )


def delete_index_mapping(collection_id):
    client = get_client()
    client.delete(index=MAPPING_INDEX_NAME, id=collection_id, refresh=True)


def get_collection_mappings():
    client = get_client()
    if not client.indices.exists(index=MAPPING_INDEX_NAME):
        return []
    query = {
        "size": 10000,  # this is the maximum allowed value
        "query": {"match_all": {}},
    }
    response = client.search(body=query, index=MAPPING_INDEX_NAME)
    collections = [
        {
            "collection_name": hit["_source"]["collection_name"],
            "collection_id": hit["_id"],
        }
        for hit in response["hits"]["hits"]
    ]
    return collections


def get_collection_mapping(collection_name: str):
    client = get_client()
    if not client.indices.exists(index=MAPPING_INDEX_NAME):
        return None
    query = {
        "size": 1,
        "query": {"bool": {"filter": [{"term": {"collection_name": collection_name}}]}},
    }
    response = client.search(body=query, index=MAPPING_INDEX_NAME)
    ids = [hit["_id"] for hit in response["hits"]["hits"]]
    if ids:
        return ids[0]
    return None


def get_opensearch_collection_info(collection_id: str):
    client = get_client()
    if not client.indices.exists(index=MAPPING_INDEX_NAME):
        return None
    item = client.get(index=MAPPING_INDEX_NAME, id=collection_id)
    return {
        "collection_id": item["_id"],
        "collection_name": item["_source"]["collection_name"],
    }


def delete_collection_indices(collection_id: str):
    client = get_client()
    # get all indices in alias
    indices = client.indices.resolve_index(name=collection_id)["aliases"][0]["indices"]
    # deleting all indices also removes the alias
    response = client.indices.delete(index=",".join(indices))
    if not response["acknowledged"]:
        print(f"Failed to delete indices for {collection_id}")
        return False
    return True


def add_document_metadata(collection_id, doc):
    client = get_client()
    # TODO: this might be counting binaries too?
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
    doc["page_count"] = client.count(body=query, index=collection_id)["count"]
    query = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"doc_id": doc["id"]}},
                    {"term": {"doc_index": doc["index"]}},
                ],
                "must": {
                    "exists": {"field": "document_vector"}  # we want vectors only here
                },
            }
        }
    }
    doc["vector_count"] = client.count(body=query, index=collection_id)["count"]
    return doc


def get_document(collection_id: str, doc_lookup_id: str):
    client = get_client()
    lookup_index = f"{collection_id}.document_lookup"
    lookup = client.get(index=lookup_index, id=doc_lookup_id)
    doc_index = lookup["_source"]["doc_index"]
    doc_id = lookup["_source"]["doc_id"]
    item = client.get(index=doc_index, id=doc_id)
    doc = {**item["_source"], "id": item["_id"], "index": item["_index"]}
    doc = add_document_metadata(collection_id, doc)
    doc["doc_lookup_id"] = doc_lookup_id
    return doc


def get_opensearch_documents(collection_id: str):
    client = get_client()
    # get all indices in alias
    indices = client.indices.resolve_index(name=collection_id)["aliases"][0]["indices"]
    # locate top level indices in collection alias
    mappings = client.indices.get_mapping(index=",".join(indices))
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
        "size": 10000,  # this is the maximum allowed value
        "query": {"match_all": {}},
    }
    response = client.search(body=query, index=",".join(top_level))
    docs = [
        {**hit["_source"], "id": hit["_id"], "index": hit["_index"]}
        for hit in response["hits"]["hits"]
    ]
    for doc in docs:
        add_document_metadata(collection_id, doc)
        query = {
            "size": 1,
            "query": {"bool": {"filter": [{"term": {"doc_id": doc["id"]}}]}},
        }
        doc["doc_lookup_id"] = client.search(
            body=query, index=f"{collection_id}.document_lookup"
        )["hits"]["hits"][0]["_id"]

    return docs


def delete_opensearch_document(collection_id: str, doc_lookup_id: str):
    client = get_client()
    lookup_index = f"{collection_id}.document_lookup"
    lookup = client.get(index=lookup_index, id=doc_lookup_id)
    doc_index = lookup["_source"]["doc_index"]
    doc_id = lookup["_source"]["doc_id"]
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
    response = client.delete_by_query(body=query, index=collection_id)
    deleted_count = response["deleted"]
    client.delete(index=doc_index, id=doc_id, refresh=True)
    return deleted_count + 1


def set_temp_file(file_path: str):
    client = get_client()
    if not client.indices.exists(index=FILES_INDEX_NAME):
        index_body = {"mappings": {"properties": {"file_path": {"type": "keyword"}}}}
        client.indices.create(index=FILES_INDEX_NAME, body=index_body)
    response = client.index(
        index=FILES_INDEX_NAME,
        body={"file_path": file_path},
        refresh=True,
    )
    return response["_id"]


def get_temp_file(id: str):
    client = get_client()
    if client.indices.exists(index=FILES_INDEX_NAME):
        response = client.get(index=FILES_INDEX_NAME, id=id)
        return response["_source"]["file_path"]
