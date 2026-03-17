import os
from opensearchpy import OpenSearch


MAPPING_INDEX_NAME = "collection_mappings"
FILES_INDEX_NAME = "file_mappings"
OPENSEARCH_MAX_RESULTS = 10000


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
                "binary_path": {"type": "keyword"},
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
        "size": OPENSEARCH_MAX_RESULTS,
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


def freeze_collection_and_get_file_paths(collection_id: str):
    client = get_client()
    paths = []
    client.indices.add_block(
        index=collection_id, block="read_only"
    )  # avoid additional writes to the index while we retrieve the list of file paths
    pit_id = client.create_pit(index=collection_id, keep_alive="100m")["pit_id"]
    body = {
        "_source": {"includes": ["binary_path"]},
        "size": OPENSEARCH_MAX_RESULTS,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"type": "document"}},
                    {"exists": {"field": "binary_path"}},
                ]
            }
        },
        "pit": {"id": pit_id, "keep_alive": "100m"},
        "sort": [{"ingest_date": {"order": "asc"}}],
    }
    response = client.search(body=body)
    while len(response["hits"]["hits"]):
        paths = [
            *paths,
            *[hit["_source"]["binary_path"] for hit in response["hits"]["hits"]],
        ]
        body["search_after"] = response["hits"]["hits"][-1]["sort"]
        response = client.search(body=body)
    return paths


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
                "must": [
                    {
                        "bool": {
                            "filter": [
                                {"term": {"type": "page"}},
                            ]
                        }
                    },
                    {
                        "has_parent": {
                            "parent_type": "document",
                            "query": {
                                "bool": {
                                    "filter": [
                                        {"term": {"_id": doc["id"]}},
                                    ],
                                }
                            },
                        }
                    },
                ]
            }
        }
    }
    doc["page_count"] = client.count(body=page_query, index=collection_id)["count"]
    vector_query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "filter": [
                                {"term": {"type": "vector"}},
                            ]
                        }
                    },
                    {
                        "has_parent": {
                            "parent_type": "document",
                            "query": {
                                "bool": {
                                    "filter": [
                                        {"term": {"_id": doc["id"]}},
                                    ],
                                }
                            },
                        }
                    },
                ]
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


def get_document_file_path(collection_id: str, doc_id: str):
    client = get_client()
    item = client.get(index=collection_id, id=doc_id)
    if "binary_path" in item["_source"]:
        return item["_source"]["binary_path"]
    return None


def get_opensearch_documents(
    collection_id: str, search, sort, max_results, filter_document_type, page=0
):
    client = get_client()
    if not search:
        filter = [{"term": {"type": "document"}}]
        if filter_document_type:
            filter.append({"terms": {"media_type": filter_document_type}})
        body = {
            "size": max_results or OPENSEARCH_MAX_RESULTS,
            "query": {"bool": {"filter": filter}},
        }
    else:
        body = {
            "_source": {"excludes": ["document_vector"]},
            "size": max_results or OPENSEARCH_MAX_RESULTS,
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
                                            "score_mode": "max",
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
        if filter_document_type:
            body["query"]["bool"]["filter"] = [
                {"terms": {"media_type": filter_document_type}}
            ]
    if max_results and page:
        body["from"] = max_results * page
    if sort:
        if sort == "date_asc":
            body["sort"] = {"ingest_date": {"order": "asc"}}
        if sort == "date_desc":
            body["sort"] = {"ingest_date": {"order": "desc"}}
    response = client.search(body=body, index=collection_id)
    docs = [
        add_document_metadata(collection_id, {**hit["_source"], "id": hit["_id"]})
        for hit in response["hits"]["hits"]
    ]
    body = {"query": {"bool": {"filter": [{"term": {"type": "document"}}]}}}
    count_response = client.count(body=body, index=collection_id)

    return {
        "documents": docs,
        "total_hits": response["hits"]["total"]["value"],
        "total_documents": count_response["count"],
    }


def get_opensearch_document_types(collection_id: str):
    client = get_client()
    body = {
        "size": 0,
        "aggs": {
            "document_type": {
                "terms": {"field": "media_type", "size": OPENSEARCH_MAX_RESULTS}
            }
        },
        "query": {"bool": {"filter": {"term": {"type": "document"}}}},
    }
    response = client.search(body=body, index=collection_id)
    return [
        bucket["key"] for bucket in response["aggregations"]["document_type"]["buckets"]
    ]


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
