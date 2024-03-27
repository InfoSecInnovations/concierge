from shiny import App, ui, Inputs, Outputs, Session
from concierge_backend_lib.collections import init_collection
from modules import home_ui, loader_ui, loader_server

UPLOADS_DIR = "uploads"
COLLECTION = "facts"

collection = init_collection(COLLECTION)

def prompter():
    return [
        ui.markdown("# Prompter")
    ]

app_ui = ui.page_auto(
    ui.navset_pill_list(
        ui.nav_panel("Home", home_ui("home")),
        ui.nav_panel("Loader", loader_ui("loader")),
        ui.nav_panel("Prompter", prompter()),
        id="navbar"
    )
)

def server(input: Inputs, output: Outputs, session: Session):
    loader_server("loader", collection, UPLOADS_DIR)
            

app = App(app_ui, server)

