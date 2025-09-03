from .opensearch import get_client
from fastapi.responses import Response
from urllib.parse import quote


async def serve_binary(collection_id: str, doc_id: str):
    client = get_client()
    lookup = client.get(index=f"{collection_id}.document_lookup", id=doc_id)
    client_response = client.search(
        body={
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"doc_id": lookup["_source"]["doc_id"]}},
                        {"term": {"doc_index": lookup["_source"]["doc_index"]}},
                    ]
                }
            }
        },
        index=f"{collection_id}.binary",
    )
    binary = client_response["hits"]["hits"][0]["_source"]["data"]
    media_type = client_response["hits"]["hits"][0]["_source"]["media_type"]
    filename = client_response["hits"]["hits"][0]["_source"]["filename"]
    content_disposition_filename = quote(filename)
    if content_disposition_filename != filename:
        content_disposition = f"inline; filename*=utf-8''{content_disposition_filename}"
    else:
        content_disposition = f'inline; filename="{filename}"'
    return Response(
        bytes.fromhex(binary),
        media_type=media_type,
        headers={"content-disposition": content_disposition},
    )
