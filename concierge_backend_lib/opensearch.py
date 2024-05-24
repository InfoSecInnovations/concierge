import os
from dotenv import load_dotenv
from opensearchpy import OpenSearch, helpers
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

load_dotenv()
OPENSEARCH_INITIAL_ADMIN_PASSWORD = os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD")

chunk_size = 200
chunk_overlap = 25

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)

def get_client():
    host = 'localhost'
    port = 9200
    auth = ('admin', OPENSEARCH_INITIAL_ADMIN_PASSWORD)

    return OpenSearch(
        hosts = [{'host': host, 'port': port}],
        http_auth = auth,
        use_ssl=True,
        verify_certs = False,
        ssl_show_warn=False
    )

def ensure_index(client, index_name):
    index_body = {
        "settings": {
            "index": {
                "knn": True
            }
        },
        "mappings": {
            "properties": {
                "document_vector": {
                    "type": "knn_vector",
                    "dimension": 384,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene",
                        "parameters": {}
                    }
                },
                "metadata": {
                    "properties": {
                        "page": {
                            "type": "unsigned_long"
                        },
                        "filename": {
                            "type": "keyword"
                        },
                        "source": {
                            "type": "keyword"
                        },
                        "title": {
                            "type": "keyword"
                        },
                        "language": {
                            "type": "keyword"
                        },
                        "ingest_date": {
                            "type": "date"
                        }
                    }
                },
                "metadata_type": {
                    "type": "keyword"
                }
            }
        }
    }

    if not client.indices.exists(index_name):
        client.indices.create(
            index_name, 
            body=index_body
        )

def insert (client, index_name, pages):
    entries = []
    total = len(pages)

    for index, page in enumerate(pages):      
        chunks = splitter.split_text(page["content"])
        for chunk in chunks:
            vect = stransform.encode(chunk)
            entry = {
                "_index": index_name,
                "metadata_type":page["metadata_type"],
                "metadata":page["metadata"],
                "text":chunk,
                "document_vector":vect
            }
            entries.append(entry)
        yield (index, total)
    helpers.bulk(client, entries, refresh=True)

def insert_with_tqdm (client, index_name, pages):
    page_progress = tqdm(total=len(pages))
    for x in insert(client, index_name, pages):
        page_progress.n = x[0] + 1
        page_progress.refresh()
    page_progress.close()

def get_context(client, index_name, reference_limit, user_input):
    query = {
        'size': reference_limit,
        "query": {
            "knn": {
                "document_vector": {
                    "vector": stransform.encode(user_input),
                    "min_score": 0.8 # this is quite a magic number, tweak as needed!
                }
            }
        },
        "_source": {
            "includes": ["metadata_type", "metadata", "text"]
        }
    }

    response = client.search(
        body = query,
        index = index_name
    )

    hits = [hit["_source"] for hit in response["hits"]["hits"]]

    return {
        "context": "\n".join([hit["text"] for hit in hits]),
        "sources": [{
            "type": hit["metadata_type"],
            "metadata": hit["metadata"]
        } for hit in hits]
    }

def get_indices(client):
    response = client.indices.get("*")
    # TODO: we must be able to do this in OpenSearch somehow?
    response = {k: v for k, v in response.items() if "document_vector" in v["mappings"]["properties"] and v["mappings"]["properties"]["document_vector"]["type"] == "knn_vector"}
    return list(response.keys())

def delete_index(client, index_name):
    response = client.indices.delete(
        index = index_name
    )
    return response["acknowledged"]

def get_documents(client, index_name):
    query = {
        "size": 0,
        "aggs": {
            "documents": {
                "multi_terms": {
                    "size": 100000,
                    "terms": [
                        {
                            "field": "metadata_type"
                        },
                        {
                            "field": "metadata.source",
                        }
                    ]
                }
            }
        }
    }

    response = client.search(
        body = query,
        index = index_name
    )

    return [{"type": bucket["key"][0], "source": bucket["key"][1], "vector_count": bucket["doc_count"]} for bucket in response["aggregations"]["documents"]["buckets"]]

def delete_document(client, index_name, type, source):
    query = {
        "query": {
            "bool": {
                "filter": [ 
                    { "term": { "metadata_type": type }},
                    { "term": { "metadata.source": source }}
                ]
            }
        }
    }
    response = client.delete_by_query(
        body = query,
        index = index_name,
        refresh = True
    )

    return response["deleted"]