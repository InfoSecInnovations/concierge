from shiny import App, ui, Inputs, Outputs, Session, reactive
from home import home_ui
from loader import loader_ui, loader_server
from prompter import prompter_ui, prompter_server
from collection_management import collection_management_ui, collection_management_server
from concierge_backend_lib.opensearch import get_indices, get_client
import os
import shinyswatch
from components import status_ui, status_server

UPLOADS_DIR = "uploads"

app_ui = ui.page_auto(
    ui.navset_pill_list(
        ui.nav_panel("Home", home_ui("home")),
        ui.nav_panel("Loader", loader_ui("loader")),
        ui.nav_panel("Prompter", prompter_ui("prompter")),
        ui.nav_panel("Collection Management", collection_management_ui("collection_management")),
        ui.nav_control(
            status_ui("status_widget"),
            shinyswatch.theme_picker_ui(default="pulse")
        ),
        id="navbar"
    ),
)

def server(input: Inputs, output: Outputs, session: Session):

    opensearch_status = reactive.value(False)
    ollama_status = reactive.value(False)
    selected_collection = reactive.value("")
    collections = reactive.value([])
    client = get_client()
    loader_server("loader", UPLOADS_DIR, selected_collection, collections, opensearch_status, client)
    prompter_server("prompter", UPLOADS_DIR, selected_collection, collections, opensearch_status, client, ollama_status)
    collection_management_server("collection_management", UPLOADS_DIR, selected_collection, collections, opensearch_status, client)
    status = status_server("status_widget")
    shinyswatch.theme_picker_server()

    @reactive.effect
    def set_collections():
        if opensearch_status.get():
            collections.set(get_indices(client))
        else:
            collections.set([])

    @reactive.effect
    def update_status():
        current_status = status()
        opensearch_status.set(current_status["opensearch"])
        ollama_status.set(current_status["ollama"])

app = App(
    app_ui, 
    server, 
    static_assets={
        f"/{UPLOADS_DIR}": os.path.abspath(os.path.join(os.path.dirname(__file__), '..', UPLOADS_DIR))
    }
)

