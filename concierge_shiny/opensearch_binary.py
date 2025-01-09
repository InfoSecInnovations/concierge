from concierge_backend_lib.opensearch import get_client
from concierge_backend_lib.authorization import auth_enabled, authorize
from concierge_backend_lib.authentication import execute_async_with_token
from starlette.responses import Response, RedirectResponse
from starlette.requests import Request
from auth import load_token_from_cookies, CookieNotPresentError
from keycloak import KeycloakPostError, KeycloakAuthenticationError


async def serve_binary(request: Request):
    collection_id = request.path_params["collection_id"]
    doc_id = request.path_params["doc_id"]
    doc_type = request.path_params["doc_type"]
    if auth_enabled:
        try:
            token = load_token_from_cookies(request.cookies)
        except CookieNotPresentError:
            return RedirectResponse("/")
        try:

            def check_authorized(token):
                return authorize(token["access_token"], collection_id, "read")

            authorized = await execute_async_with_token(token, check_authorized)
            status_code = 403
        except (KeycloakPostError, KeycloakAuthenticationError) as e:
            authorized = False
            status_code = e.response_code
        if not authorized:
            return Response(content="Not authorized", status_code=status_code)

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
