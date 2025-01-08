from shiny import ui, Inputs, Outputs, Session, render, reactive, module
from concierge_backend_lib.authentication import (
    get_keycloak_client,
    AsyncTokenTaskRunner,
)
from concierge_backend_lib.authorization import auth_enabled
import json

scope = "profile email openid"


class WebAppAsyncTokenTaskRunner:
    def __init__(self, token) -> None:
        self.runner = AsyncTokenTaskRunner(token)

    async def run_async_task(self, func):
        _, result = await self.runner.run_with_token(func)
        # TODO: refresh cookie token using AJAX somehow? This doesn't seem to be required, maybe the refresh tokens remain valid?
        return result


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


class CookieNotPresentError(Exception):
    def __init__(self, message=""):
        self.message = message


def load_token_from_cookies(cookies):
    if "concierge_token_chunk_count" not in cookies:
        raise CookieNotPresentError()
    chunk_count = int(cookies["concierge_token_chunk_count"])
    token = ""
    for i in range(chunk_count):
        token += cookies[f"concierge_auth_{i}"]
    parsed_token = json.loads(token)
    return parsed_token


def get_auth_token(session):
    if not auth_enabled:
        return {
            "access_token": None
        }  # this is a dummy token that has the access_token key to not break functions that require it to be there

    try:
        token = load_token_from_cookies(session.http_conn.cookies)
    except CookieNotPresentError:
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
                        "Log in with Keycloak",
                    )
                ],
                gap="1em",
            )

        return None
    try:
        keycloak_openid = get_keycloak_client()
        keycloak_openid.userinfo(token["access_token"])
    except Exception:

        @render.ui
        def concierge_main():
            return ui.tags.script('window.location.href = "/refresh"')

        return None
    return token


def get_task_runner(session):
    token = get_auth_token(session)
    if token is None:
        return None
    return WebAppAsyncTokenTaskRunner(token)
