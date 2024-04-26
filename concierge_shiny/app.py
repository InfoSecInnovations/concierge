from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from home import home_ui
from loader import loader_ui, loader_server
from prompter import prompter_ui, prompter_server
from collection_management import collection_management_ui, collection_management_server
from concierge_backend_lib.collections import get_collections
from concierge_backend_lib.status import get_status
import os
import shinyswatch

UPLOADS_DIR = "uploads"

app_ui = ui.page_auto(
    ui.navset_pill_list(
        ui.nav_panel("Home", home_ui("home")),
        ui.nav_panel("Loader", loader_ui("loader")),
        ui.nav_panel("Prompter", prompter_ui("prompter")),
        ui.nav_panel("Collection Management", collection_management_ui("collection_management")),
        ui.nav_control(
            ui.output_ui("status_widget")
        ),
        ui.nav_control(
            shinyswatch.theme_picker_ui(default="pulse")
        ),
        id="navbar"
    ),
)

def server(input: Inputs, output: Outputs, session: Session):

    milvus_status = reactive.value(False)
    ollama_status = reactive.value(False)
    selected_collection = reactive.value("")
    collections = reactive.value([])
    loader_server("loader", UPLOADS_DIR, selected_collection, collections, milvus_status)
    prompter_server("prompter", UPLOADS_DIR, selected_collection, collections, milvus_status, ollama_status)
    collection_management_server("collection_management", UPLOADS_DIR, selected_collection, collections, milvus_status)
    shinyswatch.theme_picker_server()

    @reactive.effect
    def set_collections():
        if milvus_status.get():
            collections.set(get_collections())
        else:
            collections.set([])

    @reactive.effect
    def set_requirements_status():
        reactive.invalidate_later(10)
        status = get_status()
        milvus_status.set(status["milvus"])
        ollama_status.set(status["ollama"])

    @render.ui
    def status_widget():
        return ui.card(
            ui.markdown(f"Milvus: {'Up' if milvus_status.get() else 'Down'}"),
            ui.markdown(f"Ollama: {'Up' if ollama_status.get() else 'Down'}")
        )

app = App(
    app_ui, 
    server, 
    static_assets={
        f"/{UPLOADS_DIR}": os.path.abspath(os.path.join(os.path.dirname(__file__), '..', UPLOADS_DIR))
    }
)

