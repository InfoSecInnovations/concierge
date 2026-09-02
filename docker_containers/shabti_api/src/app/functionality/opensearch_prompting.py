import asyncio
from .embeddings import create_embeddings
from .opensearch import get_client, get_document


async def get_context_from_opensearch(
    collection_id: str, reference_limit: int, user_input: str
):
    client = get_client()

    # the embeddings server is reached with blocking requests, so it goes in a thread
    embedding = await asyncio.to_thread(create_embeddings, user_input)

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
        "_source": {"includes": ["page_id", "text", "child_item_to_document"]},
    }

    response = await client.search(body=query, index=collection_id)

    hits = [hit["_source"] for hit in response["hits"]["hits"]]

    page_metadata = {}

    for hit in hits:
        if hit["page_id"] not in page_metadata:
            page_response = await client.get(index=collection_id, id=hit["page_id"])
            page_metadata[hit["page_id"]] = {**page_response["_source"]}

    doc_metadata = {}

    for value in page_metadata.values():
        if value["child_item_to_document"]["parent"] not in doc_metadata:
            doc_metadata[
                value["child_item_to_document"]["parent"]
            ] = await get_document(
                collection_id, value["child_item_to_document"]["parent"]
            )

    sources = []

    for hit in hits:
        page = page_metadata[hit["page_id"]]
        doc = doc_metadata[page["child_item_to_document"]["parent"]]
        sources.append(
            {"page_metadata": page, "doc_metadata": {**doc, "document_id": doc["id"]}}
        )

    return {
        "context": "\n".join([hit["text"] for hit in hits]),
        "sources": sources,
    }
