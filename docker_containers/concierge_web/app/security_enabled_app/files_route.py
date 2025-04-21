from starlette.responses import Response
from starlette.requests import Request
from concierge_api_client import ConciergeAuthorizationClient
from concierge_keycloak import get_keycloak_client
from .auth import load_token_from_cookies
from .get_api_url import get_api_url
import ssl
import os


async def serve_files(request: Request):
    token = load_token_from_cookies(request.cookies)
    client = ConciergeAuthorizationClient(
        server_url=get_api_url(),
        token=token,
        keycloak_client=get_keycloak_client(),
        verify=ssl.create_default_context(cafile=os.getenv("ROOT_CA")),
    )
    collection_id = request.path_params["collection_id"]
    doc_id = request.path_params["doc_id"]
    doc_type = request.path_params["doc_type"]
    file = await client.get_file(collection_id, doc_type, doc_id)
    return Response(file.bytes, media_type=file.media_type)
