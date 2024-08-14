from shiny import App, ui, Inputs, Outputs, Session, render, reactive
import dotenv
import os
from requests_oauthlib import OAuth2Session
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from auth_callback import auth_callback
import json
from concierge_backend_lib.opensearch import get_client, get_collections
import requests
import jwcrypto.jwk
import jwcrypto.jwt

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
redirect_uri = "http://127.0.0.1:15130/callback/"
scope = ["openid", "email", "profile"]
authorization_endpoint = "https://accounts.google.com/o/oauth2/auth"
token_endpoint = "https://accounts.google.com/o/oauth2/token"
oauth_config_url = "https://accounts.google.com/.well-known/openid-configuration"

app_ui = ui.page_auto(ui.output_ui("openid_data"))


def server(input: Inputs, output: Outputs, session: Session):
    if "concierge_auth" in session.http_conn.cookies:
        token = session.http_conn.cookies["concierge_auth"]
        oauth = OAuth2Session(client_id, token=json.loads(token))
        parsed_token = json.loads(token)
        oidc_config = requests.get(oauth_config_url).json()
        jwks_url = oidc_config["jwks_uri"]
        id_token_keys = jwcrypto.jwk.JWKSet.from_json(requests.get(jwks_url).text)
        jwt = jwcrypto.jwt.JWT(
            jwt=parsed_token["id_token"],
            key=id_token_keys,
            algs=oidc_config["id_token_signing_alg_values_supported"],
        )
        print(jwt.claims)
        r = oauth.get("https://www.googleapis.com/oauth2/v1/userinfo").json()

        client = get_client(parsed_token["id_token"])
        collections = reactive.value(get_collections(client))

        @render.ui
        def openid_data():
            return ui.TagList(
                ui.markdown("## Profile Info"),
                ui.markdown(r["email"]),
                ui.markdown(r["name"]),
                ui.markdown(f"![profile image]({r['picture']})"),
                ui.markdown("## Collections"),
                ui.markdown(", ".join(collections.get())),
            )

        return

    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    authorization_url, state = oauth.authorization_url(
        authorization_endpoint,
        # access_type and prompt are Google specific extra
        # parameters.
        access_type="offline",
        prompt="select_account",
    )

    @render.ui
    def openid_data():
        return ui.markdown(f"<{authorization_url}>")


shiny_app = App(app_ui, server)

routes = [
    Route("/callback/", endpoint=auth_callback),
    Mount("/", app=shiny_app),
]

app = Starlette(routes=routes)
