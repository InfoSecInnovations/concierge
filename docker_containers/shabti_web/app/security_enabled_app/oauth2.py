from starlette.responses import RedirectResponse
from starlette.requests import Request
import json
from shabti_keycloak import get_keycloak_client

max_bytes = 3000  # setting a cookie adds escape characters to the stringified JSON so this allows a safe margin to avoid hitting the 4096 byte limit


def set_token_cookies(token, response):
    str_token = json.dumps(token)
    bytes_token = str_token.encode()
    token_chunks = [
        bytes_token[i : i + max_bytes] for i in range(0, len(bytes_token), max_bytes)
    ]
    response.set_cookie("shabti_token_chunk_count", len(token_chunks), httponly=True)
    for index, chunk in enumerate(token_chunks):
        response.set_cookie(f"shabti_auth_{index}", chunk.decode(), httponly=True)


def get_token_from_cookies(request: Request):
    chunk_count = int(request.cookies.get("shabti_token_chunk_count"))
    if not chunk_count:
        return None
    token_string = ""
    for i in range(chunk_count):
        token_string += request.cookies.get(f"shabti_auth_{i}")
    return json.loads(token_string)


async def auth_callback(request: Request):
    keycloak_openid = get_keycloak_client()
    redirect_uri = f"{request.base_url}callback"
    token = keycloak_openid.token(
        grant_type="authorization_code",
        code=request.query_params.get("code"),
        redirect_uri=redirect_uri,
    )
    response = RedirectResponse(url="/")
    set_token_cookies(token, response)
    return response


async def refresh(request: Request):
    token = get_token_from_cookies(request)
    keycloak_openid = get_keycloak_client()
    try:
        token = keycloak_openid.refresh_token(token["refresh_token"])
    except Exception:
        return await logout(request)
    response = RedirectResponse(url="/")
    set_token_cookies(token, response)
    return response


async def logout(request: Request):
    token = get_token_from_cookies(request)
    if token:
        keycloak_openid = get_keycloak_client()
        await keycloak_openid.a_logout(token["refresh_token"])
    chunk_count = int(request.cookies.get("shabti_token_chunk_count"))
    response = RedirectResponse(url="/")
    response.delete_cookie("shabti_token_chunk_count")
    for index in range(chunk_count):
        response.delete_cookie(f"shabti_auth_{index}")
    return response
