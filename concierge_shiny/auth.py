from shiny import ui
from shiny import render
from concierge_backend_lib.opensearch import get_client
from oauth2 import oauth_configs, oauth_config_data
import json
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError
import os
from concierge_util.config import load_config
import dotenv

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
scope = ["openid profile email offline_access"]


def get_authorized_client(session):
    config = load_config()
    if not config or not config["auth"]:
        return (get_client(), None)

    if (
        "concierge_token_chunk_count" not in session.http_conn.cookies
        or "concierge_auth_provider" not in session.http_conn.cookies
    ):
        urls = []
        redirect_uri = f"{session.http_conn.headers["origin"]}/callback/"

        for provider, data in oauth_config_data.items():
            config = oauth_configs[provider]
            oauth = OAuth2Session(
                client_id=os.getenv(data["id_env_var"]),
                redirect_uri=redirect_uri + provider,
                scope=scope,
            )
            authorization_url, state = oauth.authorization_url(
                config["authorization_endpoint"]
            )
            urls.append(authorization_url)

        @render.ui
        def concierge_main():
            return ui.markdown("\n\n".join([f"<{url}>" for url in urls]))

        return (None, None)

    chunk_count = int(session.http_conn.cookies["concierge_token_chunk_count"])
    token = ""
    for i in range(chunk_count):
        token += session.http_conn.cookies[f"concierge_auth_{i}"]
    provider = session.http_conn.cookies["concierge_auth_provider"]
    oidc_config = oauth_configs[provider]
    data = oauth_config_data[provider]
    parsed_token = json.loads(token)
    oauth = OAuth2Session(client_id=os.getenv(data["id_env_var"]), token=parsed_token)
    try:
        oauth.get(
            oidc_config["userinfo_endpoint"]
        ).json()  # TODO: maybe do something with the user info?
    except TokenExpiredError:

        @render.ui
        def concierge_main():
            return ui.tags.script('window.location.href = "/refresh"')

        return (None, None)

    return (get_client(parsed_token["id_token"]), parsed_token["id_token"])
