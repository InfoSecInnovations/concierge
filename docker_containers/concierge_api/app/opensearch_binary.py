from .opensearch import get_client
from fastapi.responses import Response


async def serve_binary(collection_id: str, doc_id: str, doc_type: str):
    client = get_client()
    response = client.search(
        body={
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"doc_id": doc_id}},
                        {"term": {"doc_index": f"{collection_id}.{doc_type}"}},
                    ]
                }
            }
        },
        index=f"{collection_id}.binary",
    )
    binary = response["hits"]["hits"][0]["_source"]["data"]
    media_type = response["hits"]["hits"][0]["_source"]["media_type"]
    return Response(bytes.fromhex(binary), media_type=media_type)  # TODO: proper type
