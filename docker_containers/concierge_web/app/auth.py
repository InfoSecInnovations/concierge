from shiny import ui, render
from concierge_keycloak import get_keycloak_client
from concierge_util import auth_enabled
import json


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
