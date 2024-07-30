from shiny import App, ui, Inputs, Outputs, Session, reactive
from home import home_ui
from prompter import prompter_ui, prompter_server
from collection_management import collection_management_ui, collection_management_server
from concierge_backend_lib.opensearch import get_collections, get_client
import shinyswatch
from components import status_ui, status_server
from isi_util.async_single import asyncify
from opensearch_binary import serve_binary
from starlette.applications import Starlette
from starlette.routing import Mount, Route

app_ui = ui.page_auto(
    ui.navset_pill_list(
        ui.nav_panel("Home", home_ui("home")),
        ui.nav_panel("Prompter", prompter_ui("prompter")),
        ui.nav_panel(
            "Collection Management", collection_management_ui("collection_management")
        ),
        ui.nav_control(status_ui("status_widget"), shinyswatch.theme_picker_ui()),
        id="navbar",
    ),
    theme=shinyswatch.theme.pulse,
)


def server(input: Inputs, output: Outputs, session: Session):
    opensearch_status = reactive.value(False)
    ollama_status = reactive.value(False)
    selected_collection = reactive.value("")
    collections = reactive.value([])
    client = get_client()
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
    status = status_server("status_widget")
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
    Route("/files/{collection_name}/{doc_type}/{doc_id}", endpoint=serve_binary),
    Mount("/", app=shiny_app),
]


app = Starlette(routes=routes)
