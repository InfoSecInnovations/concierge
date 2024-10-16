from shiny import ui, Inputs, Outputs, Session, render, reactive, module
from concierge_backend_lib.authentication import keycloak_config, get_keycloak_client
import json
import dotenv

dotenv.load_dotenv()

scope = "profile email openid"


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
        return None

    if "concierge_token_chunk_count" not in session.http_conn.cookies:
        redirect_uri = f"{session.http_conn.headers["origin"]}/callback"
        keycloak_openid = get_keycloak_client()
        authorization_url = keycloak_openid.auth_url(
            redirect_uri=redirect_uri, scope=scope
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

        return None

    chunk_count = int(session.http_conn.cookies["concierge_token_chunk_count"])
    token = ""
    for i in range(chunk_count):
        token += session.http_conn.cookies[f"concierge_auth_{i}"]
    parsed_token = json.loads(token)
    try:
        keycloak_openid = get_keycloak_client()
        keycloak_openid.userinfo(
            parsed_token["access_token"]
        )  # TODO: maybe do something with the user info?
    except Exception:

        @render.ui
        def concierge_main():
            return ui.tags.script('window.location.href = "/refresh"')

        return None
    return parsed_token
