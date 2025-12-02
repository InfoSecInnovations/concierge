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
    collection_index_name = collection_id
    collection_index_body = {
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
                "filename": {"type": "wildcard"},
                "source": {"type": "wildcard"},
                "media_type": {"type": "keyword"},
                "ingest_date": {"type": "unsigned_long"},
                "languages": {"type": "keyword"},
                "text": {"type": "text"},
                "binary_data": {"type": "binary"},
                "page_number": {"type": "integer"},
                "type": {"type": "keyword"},
                "child_item_to_document": {
                    "type": "join",
                    "relations": {"document": "child_item"},
                },
            }
        },
    }
    client.indices.create(index=collection_index_name, body=collection_index_body)


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
    response = client.indices.delete(index=collection_id)
    if not response["acknowledged"]:
        print(f"Failed to delete indices for {collection_id}")
        return False
    return True


def add_document_metadata(collection_id, doc):
    client = get_client()
    page_query = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"doc_id": doc["id"]}},
                    {"exists": {"field": "page_number"}},
                ],
            }
        }
    }
    doc["page_count"] = client.count(body=page_query, index=collection_id)["count"]
    vector_query = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"doc_id": doc["id"]}},
                    {"exists": {"field": "document_vector"}},
                ],
            }
        }
    }
    doc["vector_count"] = client.count(body=vector_query, index=collection_id)["count"]
    return doc


def get_document(collection_id: str, doc_id: str):
    client = get_client()
    item = client.get(index=collection_id, id=doc_id)
    doc = {**item["_source"], "id": item["_id"]}
    doc = add_document_metadata(collection_id, doc)
    return doc


def get_opensearch_documents(
    collection_id: str, search, sort, max_results, filter_document_type
):
    client = get_client()
    if not search:
        body = {
            "size": max_results or 10000,  # this is the maximum allowed value
            "query": {"bool": {"filter": {"term": {"type": "document"}}}},
        }
        response = client.search(body=body, index=collection_id)
        docs = [
            add_document_metadata(collection_id, {**hit["_source"], "id": hit["_id"]})
            for hit in response["hits"]["hits"]
        ]
    else:
        body = {
            "_source": {"excludes": ["document_vector"]},
            "size": 0,
            "query": {
                "bool": {
                    "should": [
                        {
                            "bool": {
                                "boost": 100,
                                "minimum_should_match": 1,
                                "should": [
                                    {"wildcard": {"filename": f"*{search}*"}},
                                    {"wildcard": {"source": f"*{search}*"}},
                                    {"term": {"_id": {"value": search}}},
                                ],
                                "filter": {"term": {"type": "document"}},
                            }
                        },
                        {
                            "bool": {
                                "must": [
                                    {
                                        "has_child": {
                                            "type": "child_item",
                                            "query": {"match": {"text": search}},
                                        }
                                    }
                                ]
                            }
                        },
                    ]
                }
            },
        }
        response = client.search(body=body, index=collection_id)
        docs = [
            add_document_metadata(collection_id, {**hit["_source"], "id": hit["_id"]})
            for hit in response["hits"]["hits"]
        ]

    return docs


def delete_opensearch_document(collection_id: str, doc_id: str):
    client = get_client()
    child_query = {
        "query": {
            "has_parent": {
                "parent_type": "document",
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"_id": doc_id}},
                        ],
                    }
                },
            }
        }
    }
    client.delete_by_query(index=collection_id, body=child_query, refresh=True)
    client.delete(index=collection_id, id=doc_id, refresh=True)
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
