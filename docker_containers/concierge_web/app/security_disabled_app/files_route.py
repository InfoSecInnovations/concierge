from starlette.responses import Response
from starlette.requests import Request
from concierge_api_client import ConciergeClient

API_URL = "http://127.0.0.1:8000/" # TODO: get this from the environment

async def serve_files(request: Request):
    client = ConciergeClient(server_url=API_URL)
    collection_id = request.path_params["collection_id"]
    doc_id = request.path_params["doc_id"]
    doc_type = request.path_params["doc_type"]
    file = await client.get_file(collection_id, doc_type, doc_id)
    return Response(file.bytes, media_type=file.media_type)