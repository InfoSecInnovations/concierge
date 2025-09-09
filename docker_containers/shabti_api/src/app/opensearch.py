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
    collection_index_name = f"{collection_id}.vectors"
    collection_index_body = {
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
                "page_id": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
            }
        },
    }
    client.indices.create(index=collection_index_name, body=collection_index_body)
    documents_index_name = f"{collection_id}.documents"
    documents_index_body = {
        "aliases": {collection_id: {}},
        "mappings": {
            "properties": {
                "filename": {"type": "keyword"},
                "source": {"type": "keyword"},
                "media_type": {"type": "keyword"},
                "ingest_date": {"type": "unsigned_long"},
                "languages": {"type": "keyword"},
            }
        },
    }
    client.indices.create(index=documents_index_name, body=documents_index_body)
    binary_index_name = f"{collection_id}.binary"
    binary_index_body = {
        "aliases": {collection_id: {}},
        "mappings": {
            "properties": {
                "doc_id": {"type": "keyword"},
                "data": {"type": "binary"},
                "media_type": {"type": "keyword"},
                "filename": {"type": "keyword"},
            }
        },
    }
    client.indices.create(index=binary_index_name, body=binary_index_body)
    pages_index_name = f"{collection_id}.pages"
    pages_index_body = {
        "aliases": {collection_id: {}},
        "mappings": {
            "properties": {
                "doc_id": {"type": "keyword"},
                "page_number": {"type": "integer"},
                "source": {"type": "keyword"},
            }
        },
    }
    client.indices.create(index=pages_index_name, body=pages_index_body)


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
    query = {
        "query": {
            "bool": {
                "filter": [{"term": {"doc_id": doc["id"]}}],
            }
        }
    }
    doc["page_count"] = client.count(body=query, index=f"{collection_id}.pages")[
        "count"
    ]
    query = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"doc_id": doc["id"]}},
                ],
            }
        }
    }
    doc["vector_count"] = client.count(body=query, index=f"{collection_id}.vectors")[
        "count"
    ]
    return doc


def get_document(collection_id: str, doc_id: str):
    client = get_client()
    doc_index = f"{collection_id}.documents"
    item = client.get(index=doc_index, id=doc_id)
    doc = {**item["_source"], "id": item["_id"]}
    doc = add_document_metadata(collection_id, doc)
    return doc


def get_opensearch_documents(collection_id: str):
    client = get_client()
    document_index_name = f"{collection_id}.documents"
    # get documents from all of these
    query = {
        "size": 10000,  # this is the maximum allowed value
        "query": {"match_all": {}},
    }
    response = client.search(body=query, index=document_index_name)
    docs = [{**hit["_source"], "id": hit["_id"]} for hit in response["hits"]["hits"]]
    for doc in docs:
        add_document_metadata(collection_id, doc)

    return docs


def delete_opensearch_document(collection_id: str, doc_id: str):
    client = get_client()
    doc_index_name = f"{collection_id}.documents"
    client.delete(index=doc_index_name, id=doc_id, refresh=True)
    return 1  # TODO: evaluate what we should actually return here


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
