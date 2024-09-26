from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from home import home_ui
from prompter import prompter_ui, prompter_server
from collection_management import collection_management_ui, collection_management_server
from concierge_backend_lib.opensearch import get_collections
import shinyswatch
from components import status_ui, status_server
from isi_util.async_single import asyncify
from opensearch_binary import serve_binary
from oauth2 import auth_callback, refresh, logout
from starlette.applications import Starlette
from starlette.routing import Mount, Route
import os
import dotenv
from auth import get_authorized_client

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
scope = ["openid profile email offline_access"]

app_ui = ui.page_auto(
    ui.output_ui("concierge_main"),
    theme=shinyswatch.theme.pulse,
)


def server(input: Inputs, output: Outputs, session: Session):
    shinyswatch.theme_picker_server()
    client, token = get_authorized_client(session)
    if not client:
        return
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
            ui.nav_control(
                ui.input_action_button("openid_logout", "Log Out", class_="my-3")
            )
            if token
            else None,
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
    status = status_server("status_widget", token)

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

    @reactive.effect
    @reactive.event(input.openid_logout, ignore_init=True, ignore_none=True)
    def handle_logout():
        @render.ui
        def concierge_main():
            return ui.tags.script('window.location.href = "/logout"')


shiny_app = App(app_ui, server)


routes = [
    Route("/callback/{provider}", endpoint=auth_callback),
    Route("/refresh", endpoint=refresh),
    Route("/logout", endpoint=logout),
    Route("/files/{collection_name}/{doc_type}/{doc_id}", endpoint=serve_binary),
    Mount("/", app=shiny_app),
]


app = Starlette(routes=routes)
