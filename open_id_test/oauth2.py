from starlette.responses import RedirectResponse
from starlette.requests import Request
import dotenv
import os
from requests_oauthlib import OAuth2Session
import json
from oid_configs import oauth_configs, oauth_config_data

dotenv.load_dotenv()
max_bytes = 4000


def set_token_cookies(token, response):
    str_token = json.dumps(token)
    bytes_token = str_token.encode()
    token_chunks = [
        bytes_token[i : i + max_bytes] for i in range(0, len(bytes_token), max_bytes)
    ]
    response.set_cookie("concierge_token_chunk_count", len(token_chunks), httponly=True)
    for index, chunk in enumerate(token_chunks):
        response.set_cookie(f"concierge_auth_{index}", chunk.decode(), httponly=True)


async def auth_callback(request: Request):
    provider = request.path_params["provider"]
    config = oauth_configs[provider]
    data = oauth_config_data[provider]
    redirect_uri = f"{request.base_url}callback/"
    oauth = OAuth2Session(
        client_id=os.getenv(data["id_env_var"]),
        state=request.query_params.get("state"),
        redirect_uri=redirect_uri + provider,
    )
    token = oauth.fetch_token(
        token_url=config["token_endpoint"],
        client_secret=os.getenv(data["secret_env_var"]),
        code=request.query_params.get("code"),
    )
    response = RedirectResponse(url="/")
    set_token_cookies(token, response)
    response.set_cookie("concierge_auth_provider", provider, httponly=True)
    return response


async def refresh(request: Request):
    provider = request.path_params["provider"]
    config = oauth_configs[provider]
    data = oauth_config_data[provider]
    chunk_count = int(request.cookies.get("concierge_token_chunk_count"))
    token_string = ""
    for i in range(chunk_count):
        token_string += request.cookies.get(f"concierge_auth_{i}")
    oauth = OAuth2Session(
        client_id=os.getenv(data["id_env_var"]), token=json.loads(token_string)
    )
    token = oauth.refresh_token(
        config["token_endpoint"],
        client_id=os.getenv(data["id_env_var"]),
        client_secret=os.getenv(data["secret_env_var"]),
    )
    response = RedirectResponse(url="/")
    set_token_cookies(token, response)
    return response
