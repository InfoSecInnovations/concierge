from starlette.responses import RedirectResponse
from starlette.requests import Request
import dotenv
import os
from requests_oauthlib import OAuth2Session
import json

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
redirect_uri = "http://127.0.0.1:15130/callback/"
scope = ["openid"]
authorization_endpoint = "https://accounts.google.com/o/oauth2/auth"
token_endpoint = "https://accounts.google.com/o/oauth2/token"


async def auth_callback(request: Request):
    oauth = OAuth2Session(
        client_id, state=request.query_params.get("state"), redirect_uri=redirect_uri
    )
    token = oauth.fetch_token(
        token_url=token_endpoint,
        client_secret=client_secret,
        code=request.query_params.get("code"),
    )
    response = RedirectResponse(url="/")
    response.set_cookie("concierge_auth", json.dumps(token), httponly=True)
    return response
