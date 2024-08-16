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
from oid_configs import oauth_configs, oauth_config_data

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
redirect_uri = "http://localhost:15130/callback/"
scope = ["openid", "profile", "email"]

app_ui = ui.page_auto(ui.output_ui("openid_data"))


def server(input: Inputs, output: Outputs, session: Session):
    if (
        "concierge_auth" in session.http_conn.cookies
        and "concierge_auth_provider" in session.http_conn.cookies
    ):
        token = session.http_conn.cookies["concierge_auth"]
        provider = session.http_conn.cookies["concierge_auth_provider"]
        oidc_config = oauth_configs[provider]
        data = oauth_config_data[provider]
        oauth = OAuth2Session(
            client_id=os.getenv(data["id_env_var"]), token=json.loads(token)
        )
        parsed_token = json.loads(token)
        jwks_url = oidc_config["jwks_uri"]
        id_token_keys = jwcrypto.jwk.JWKSet.from_json(requests.get(jwks_url).text)
        jwt = jwcrypto.jwt.JWT(
            jwt=parsed_token["id_token"],
            key=id_token_keys,
            algs=oidc_config["id_token_signing_alg_values_supported"],
        )
        print(jwt.claims)
        parsed_claims = json.loads(jwt.claims)

        client = get_client(parsed_token["id_token"])
        collections = reactive.value(get_collections(client))

        @render.ui
        def openid_data():
            return ui.TagList(
                ui.markdown("## Profile Info"),
                ui.markdown(parsed_claims["sub"]),
                ui.markdown("## Collections"),
                ui.markdown(", ".join(collections.get())),
            )

        return

    urls = []

    for provider, data in oauth_config_data.items():
        config = oauth_configs[provider]
        oauth = OAuth2Session(
            client_id=os.getenv(data["id_env_var"]),
            redirect_uri=redirect_uri + provider,
            scope=scope,
        )
        authorization_url, state = oauth.authorization_url(
            config["authorization_endpoint"],
            # access_type and prompt are Google specific extra
            # parameters.
            # access_type="offline",
            # prompt="select_account",
        )
        urls.append(authorization_url)

    @render.ui
    def openid_data():
        return ui.markdown("\n\n".join([f"<{url}>" for url in urls]))


shiny_app = App(app_ui, server)

routes = [
    Route("/callback/{provider}", endpoint=auth_callback),
    Mount("/", app=shiny_app),
]

app = Starlette(routes=routes)
