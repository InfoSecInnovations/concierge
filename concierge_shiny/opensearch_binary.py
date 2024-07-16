from concierge_backend_lib.opensearch import get_client
from starlette.responses import Response
from starlette.requests import Request


async def serve_binary(request: Request):
    client = get_client()
    collection_name = request.path_params["collection_name"]
    doc_id = request.path_params["doc_id"]
    doc_type = request.path_params["doc_type"]
    response = client.search(
        body={
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"doc_id": doc_id}},
                        {"term": {"doc_index": f"{collection_name}.{doc_type}"}},
                    ]
                }
            }
        },
        index=f"{collection_name}.binary",
    )
    binary = response["hits"]["hits"][0]["_source"]["data"]
    media_type = response["hits"]["hits"][0]["_source"]["media_type"]
    return Response(bytes.fromhex(binary), media_type=media_type)  # TODO: proper type
