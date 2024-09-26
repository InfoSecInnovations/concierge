from shiny import ui, Inputs, Outputs, Session, render, reactive, module
from concierge_backend_lib.opensearch import get_client
from oauth2 import oauth_configs, oauth_config_data
import json
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError
import os
from concierge_util import load_config
import dotenv
# import jwcrypto.jwk
# import jwcrypto.jwt
# import requests

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
scope = ["openid profile email offline_access"]


@module.ui
def login_button_ui(text):
    return [
        ui.output_ui("script_output"),
        ui.input_action_button("login_openid_button", text),
    ]


@module.server
def login_button_server(input: Inputs, output: Outputs, session: Session, url: str):
    @reactive.effect
    @reactive.event(input.login_openid_button, ignore_init=True)
    def on_click():
        @render.ui
        def script_output():
            return ui.tags.script(f'window.location.href = "{url}"')


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
            urls.append((provider, data["display_name"]))
            login_button_server(f"login_openid_{provider}", authorization_url)

        @render.ui
        def concierge_main():
            return ui.page_fillable(
                ui.markdown("# Data Concierge AI"),
                [
                    login_button_ui(f"login_openid_{url[0]}", f"Log in with {url[1]}")
                    for url in urls
                ],
                gap="1em",
            )

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
        # uncomment below to debug OpenID claims
        # jwks_url = oidc_config['jwks_uri']
        # id_token_keys = jwcrypto.jwk.JWKSet.from_json(
        #     requests.get(jwks_url).text
        # )
        # jwt = jwcrypto.jwt.JWT(
        #     jwt=parsed_token["id_token"],
        #     key=id_token_keys,
        #     algs=oidc_config['id_token_signing_alg_values_supported']
        # )
        # jwt_claims = json.loads(jwt.claims)
        # print(jwt_claims)
    except TokenExpiredError:

        @render.ui
        def concierge_main():
            return ui.tags.script('window.location.href = "/refresh"')

        return (None, None)

    return (get_client(parsed_token["id_token"]), parsed_token["id_token"])
