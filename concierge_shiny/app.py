from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from home import home_ui
from loader import loader_ui, loader_server
from prompter import prompter_ui, prompter_server
from collection_management import collection_management_ui, collection_management_server
from concierge_backend_lib.collections import get_collections
import os
import shinyswatch

UPLOADS_DIR = "uploads"

app_ui = ui.page_auto(
    ui.navset_pill_list(
        ui.nav_panel("Home", home_ui("home")),
        ui.nav_panel("Loader", loader_ui("loader")),
        ui.nav_panel("Prompter", prompter_ui("prompter")),
        ui.nav_panel("Collection Management", collection_management_ui("collection_management")),
        ui.nav_spacer(),
        ui.nav_control(
            shinyswatch.theme_picker_ui(default="pulse")
        ),
        id="navbar"
    ),
    
)

def server(input: Inputs, output: Outputs, session: Session):

    selected_collection = reactive.value("")
    collections = reactive.value(get_collections())
    loader_server("loader", UPLOADS_DIR, selected_collection, collections)
    prompter_server("prompter", UPLOADS_DIR, selected_collection, collections)
    collection_management_server("collection_management", UPLOADS_DIR, selected_collection, collections)  

    shinyswatch.theme_picker_server()

app = App(
    app_ui, 
    server, 
    static_assets={f"/{UPLOADS_DIR}": os.path.abspath(os.path.join(os.path.dirname(__file__), '..', UPLOADS_DIR))}
)

