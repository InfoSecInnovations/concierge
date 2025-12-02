from .embeddings import create_embeddings
from .opensearch import get_client, get_document


def get_context_from_opensearch(
    collection_id: str, reference_limit: int, user_input: str
):
    client = get_client()

    embedding = create_embeddings(user_input)

    query = {
        "size": reference_limit,
        "query": {
            "knn": {
                "document_vector": {
                    "vector": embedding,
                    "min_score": 0.6,  # this is quite a magic number, tweak as needed!
                }
            }
        },
        "_source": {"includes": ["page_id", "text", "doc_id"]},
    }

    response = client.search(body=query, index=collection_id)

    hits = [hit["_source"] for hit in response["hits"]["hits"]]

    page_metadata = {}

    for hit in hits:
        if hit["page_id"] not in page_metadata:
            response = client.get(index=collection_id, id=hit["page_id"])
            page_metadata[hit["page_id"]] = {**response["_source"]}

    doc_metadata = {}

    for value in page_metadata.values():
        if value["doc_id"] not in doc_metadata:
            doc_metadata[value["doc_id"]] = get_document(collection_id, value["doc_id"])

    sources = []

    for hit in hits:
        page = page_metadata[hit["page_id"]]
        doc = doc_metadata[page["doc_id"]]
        sources.append(
            {"page_metadata": page, "doc_metadata": {**doc, "document_id": doc["id"]}}
        )

    return {
        "context": "\n".join([hit["text"] for hit in hits]),
        "sources": sources,
    }
