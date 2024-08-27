from shiny import App, ui, Inputs, Outputs, Session, render, reactive
import dotenv
import os
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from oauth2 import auth_callback, refresh
import json
from concierge_backend_lib.opensearch import get_client, get_collections
from oid_configs import oauth_configs, oauth_config_data

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
redirect_uri = "http://localhost:15130/callback/"
scope = ["openid profile email offline_access"]

app_ui = ui.page_auto(ui.output_ui("openid_data"))


def server(input: Inputs, output: Outputs, session: Session):
    if (
        "concierge_token_chunk_count" in session.http_conn.cookies
        and "concierge_auth_provider" in session.http_conn.cookies
    ):
        chunk_count = int(session.http_conn.cookies["concierge_token_chunk_count"])
        token = ""
        for i in range(chunk_count):
            token += session.http_conn.cookies[f"concierge_auth_{i}"]
        provider = session.http_conn.cookies["concierge_auth_provider"]
        oidc_config = oauth_configs[provider]
        data = oauth_config_data[provider]
        parsed_token = json.loads(token)
        oauth = OAuth2Session(
            client_id=os.getenv(data["id_env_var"]), token=parsed_token
        )
        try:
            user_info = oauth.get(oidc_config["userinfo_endpoint"]).json()
        except TokenExpiredError:

            @render.ui
            def openid_data():
                return ui.tags.script(f'window.location.href = "/refresh/{provider}"')

            return

        client = get_client(parsed_token["id_token"])
        collections = reactive.value(get_collections(client))

        @render.ui
        def openid_data():
            return ui.TagList(
                ui.markdown("## Profile Info"),
                ui.markdown(user_info["sub"]),
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
            config["authorization_endpoint"]
        )
        urls.append(authorization_url)

    @render.ui
    def openid_data():
        return ui.markdown("\n\n".join([f"<{url}>" for url in urls]))


shiny_app = App(app_ui, server)

routes = [
    Route("/callback/{provider}", endpoint=auth_callback),
    Route("/refresh/{provider}", endpoint=refresh),
    Mount("/", app=shiny_app),
]

app = Starlette(routes=routes)
