from starlette.responses import RedirectResponse
from starlette.requests import Request
import dotenv
import os
from requests_oauthlib import OAuth2Session
import json
from oid_configs import oauth_configs, oauth_config_data

dotenv.load_dotenv()
redirect_uri = "http://localhost:15130/callback/"


async def auth_callback(request: Request):
    provider = request.path_params["provider"]
    config = oauth_configs[provider]
    data = oauth_config_data[provider]
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
    response.set_cookie("concierge_auth", json.dumps(token), httponly=True)
    response.set_cookie("concierge_auth_provider", provider, httponly=True)
    return response
