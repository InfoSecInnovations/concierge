from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from home import home_ui
from prompter import prompter_ui, prompter_server
from collection_management import collection_management_ui, collection_management_server
from concierge_backend_lib.opensearch import get_collections, get_client
import shinyswatch
from components import status_ui, status_server
from isi_util.async_single import asyncify
from opensearch_binary import serve_binary
from oauth2 import auth_callback, refresh
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from oid_configs import oauth_configs, oauth_config_data
import json
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError
import os
import dotenv

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
scope = ["openid profile email offline_access"]

app_ui = ui.page_auto(
    ui.output_ui("concierge_main"),
    theme=shinyswatch.theme.pulse,
)


def server(input: Inputs, output: Outputs, session: Session):
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

        return

    # TODO: only do this if security is enabled

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
            return ui.tags.script(f'window.location.href = "/refresh/{provider}"')

        return

    client = get_client(parsed_token["id_token"])

    # TODO: if security isn't enabled make basic get_client call

    opensearch_status = reactive.value(False)
    ollama_status = reactive.value(False)
    selected_collection = reactive.value("")
    collections = reactive.value([])

    @render.ui
    def concierge_main():
        return ui.navset_pill_list(
            ui.nav_panel("Home", home_ui("home")),
            ui.nav_panel("Prompter", prompter_ui("prompter")),
            ui.nav_panel(
                "Collection Management",
                collection_management_ui("collection_management"),
            ),
            ui.nav_control(status_ui("status_widget"), shinyswatch.theme_picker_ui()),
            id="navbar",
        )

    prompter_server(
        "prompter",
        selected_collection,
        collections,
        opensearch_status,
        client,
        ollama_status,
    )
    collection_management_server(
        "collection_management",
        selected_collection,
        collections,
        opensearch_status,
        client,
    )
    status = status_server(
        "status_widget", parsed_token["id_token"]
    )  # TODO: optional token
    shinyswatch.theme_picker_server()

    @reactive.extended_task
    async def set_collections():
        collections.set(await asyncify(get_collections, client))

    @reactive.effect
    def update_collections():
        if opensearch_status.get():
            set_collections()
        else:
            collections.set([])

    @reactive.effect
    def update_status():
        current_status = status()
        opensearch_status.set(current_status["opensearch"])
        ollama_status.set(current_status["ollama"])


shiny_app = App(app_ui, server)


routes = [
    Route("/callback/{provider}", endpoint=auth_callback),
    Route("/refresh/{provider}", endpoint=refresh),
    Route("/files/{collection_name}/{doc_type}/{doc_id}", endpoint=serve_binary),
    Mount("/", app=shiny_app),
]


app = Starlette(routes=routes)
