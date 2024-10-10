from shiny import ui, Inputs, Outputs, Session, render, reactive, module
from oauth2 import keycloak_config, keycloak_openid_config
import json
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError
import os
import dotenv
import jwcrypto.jwk
import jwcrypto.jwt
import requests

dotenv.load_dotenv()

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


def get_auth_tokens(session, config):
    if not config or not config["auth"]:
        return (None, None)

    if "concierge_token_chunk_count" not in session.http_conn.cookies:
        redirect_uri = f"{session.http_conn.headers["origin"]}/callback"
        oauth = OAuth2Session(
            client_id=os.getenv(keycloak_config["id_env_var"]),
            redirect_uri=redirect_uri,
            scope=scope,
        )
        authorization_url, state = oauth.authorization_url(
            keycloak_openid_config["authorization_endpoint"]
        )
        login_button_server("login_openid_keycloak", authorization_url)

        @render.ui
        def concierge_main():
            return ui.page_fillable(
                ui.markdown("# Data Concierge AI"),
                [
                    login_button_ui(
                        "login_openid_keycloak",
                        f"Log in with {keycloak_config["display_name"]}",
                    )
                ],
                gap="1em",
            )

        return (None, None)

    chunk_count = int(session.http_conn.cookies["concierge_token_chunk_count"])
    token = ""
    for i in range(chunk_count):
        token += session.http_conn.cookies[f"concierge_auth_{i}"]
    parsed_token = json.loads(token)
    oauth = OAuth2Session(
        client_id=os.getenv(keycloak_config["id_env_var"]), token=parsed_token
    )
    try:
        oauth.get(
            keycloak_openid_config["userinfo_endpoint"]
        ).json()  # TODO: maybe do something with the user info?
        jwks_url = keycloak_openid_config["jwks_uri"]
        id_token_keys = jwcrypto.jwk.JWKSet.from_json(requests.get(jwks_url).text)
        jwt = jwcrypto.jwt.JWT(
            jwt=parsed_token["id_token"],
            key=id_token_keys,
            algs=keycloak_openid_config["id_token_signing_alg_values_supported"],
        )
        jwt_claims = json.loads(jwt.claims)
        print(jwt_claims)
    except TokenExpiredError:

        @render.ui
        def concierge_main():
            return ui.tags.script('window.location.href = "/refresh"')

        return (None, None)

    return (parsed_token["id_token"], jwt_claims)
