from shiny import ui, render
from concierge_backend_lib.authentication import (
    get_keycloak_client,
    AsyncTokenTaskRunner,
)
from concierge_backend_lib.authorization import auth_enabled
import json


class WebAppAsyncTokenTaskRunner:
    def __init__(self, token) -> None:
        self.runner = AsyncTokenTaskRunner(token)

    async def run_async_task(self, func):
        _, result = await self.runner.run_with_token(func)
        # TODO: refresh cookie token using AJAX somehow? This doesn't seem to be required, maybe the refresh tokens remain valid?
        return result


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
    if not auth_enabled():
        return {
            "access_token": None
        }  # this is a dummy token that has the access_token key to not break functions that require it to be there

    try:
        token = load_token_from_cookies(session.http_conn.cookies)
    except CookieNotPresentError:

        @render.ui
        def script_output():
            return ui.tags.script('window.location.href = "/login/"')

        return None
    try:
        keycloak_openid = get_keycloak_client()
        keycloak_openid.userinfo(token["access_token"])
    except Exception:

        @render.ui
        def script_output():
            return ui.tags.script('window.location.href = "/refresh"')

        return None
    return token


def get_task_runner(session):
    token = get_auth_token(session)
    if token is None:
        return None
    return WebAppAsyncTokenTaskRunner(token)
