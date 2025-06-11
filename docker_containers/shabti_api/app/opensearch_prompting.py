from .embeddings import create_embeddings
from .opensearch import get_client


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
        "_source": {"includes": ["page_index", "page_id", "text", "doc_lookup_id"]},
    }

    response = client.search(body=query, index=f"{collection_id}.vectors")

    hits = [hit["_source"] for hit in response["hits"]["hits"]]

    page_metadata = {}

    for hit in hits:
        print(f"{hit['text']}\n")
        if hit["page_index"] not in page_metadata:
            page_metadata[hit["page_index"]] = {}
        if hit["page_id"] not in page_metadata[hit["page_index"]]:
            response = client.get(hit["page_index"], hit["page_id"])
            page_metadata[hit["page_index"]][hit["page_id"]] = {
                **response["_source"],
                "doc_lookup_id": hit["doc_lookup_id"],
            }

    doc_metadata = {}

    for item in page_metadata.values():
        for value in item.values():
            if value["doc_index"] not in doc_metadata:
                doc_metadata[value["doc_index"]] = {}
            if value["doc_id"] not in doc_metadata[value["doc_index"]]:
                response = client.get(value["doc_index"], value["doc_id"])
                doc_metadata[value["doc_index"]][value["doc_id"]] = {
                    **response["_source"],
                    "id": value["doc_id"],
                    "doc_lookup_id": value["doc_lookup_id"],
                }

    sources = []

    for hit in hits:
        page = page_metadata[hit["page_index"]][hit["page_id"]]
        doc = doc_metadata[page["doc_index"]][page["doc_id"]]
        sources.append(
            {"type": doc["type"], "page_metadata": page, "doc_metadata": doc}
        )

    return {
        "context": "\n".join([hit["text"] for hit in hits]),
        "sources": sources,
    }
