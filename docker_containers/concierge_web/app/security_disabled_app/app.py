from shiny import ui, Inputs, Outputs, Session, reactive, render, App
import shinyswatch
from concierge_api_client import ConciergeClient
from ..common.collections_data import CollectionsData
from ..common.status import status_ui, status_server
from .home import home_ui, home_server
from .collection_management import collection_management_server
from ..common.collection_management_ui import collection_management_ui
from ..common.update_status import update_status_reactives
from ..common.prompter import prompter_ui, prompter_server
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from .files_route import serve_files
from concierge_types import CollectionInfo
from .collection_selector_server import collection_selector_server

API_URL = "http://127.0.0.1:8000/"  # TODO: get this from the environment

app_ui = ui.page_auto(
    ui.output_ui("concierge_main"),
    theme=shinyswatch.theme.pulse,
)


def server(input: Inputs, output: Outputs, session: Session):
    shinyswatch.theme_picker_server()
    client = ConciergeClient(API_URL)
    opensearch_status = reactive.value(False)
    ollama_status = reactive.value(False)
    selected_collection = reactive.value("")
    collections: reactive.Value[CollectionsData[CollectionInfo]] = reactive.value(
        CollectionsData(loading=True)
    )

    @render.ui
    def concierge_main():
        return ui.navset_pill_list(
            ui.nav_panel("Home", home_ui("home")),
            ui.nav_panel(
                "Collection Management",
                collection_management_ui("collection_management"),
            ),
            ui.nav_panel("Prompter", prompter_ui("prompter")),
            ui.nav_control(status_ui("status_widget"), shinyswatch.theme_picker_ui()),
            id="concierge_nav",
        )

    home_server("home")
    status = status_server("status_widget", client)
    collection_management_server(
        "collection_management",
        client,
        selected_collection,
        collections,
        opensearch_status,
    )

    @reactive.effect
    def update_status():
        update_status_reactives(status, opensearch_status, ollama_status)

    @reactive.extended_task
    async def fetch_collections():
        return await client.get_collections()

    @reactive.effect
    def fetch_collections_effect():
        new_collections = fetch_collections.result()
        collections.set(
            CollectionsData(
                collections={
                    collection.collection_id: collection
                    for collection in new_collections
                },
                loading=False,
            )
        )
        if len(new_collections):
            selected_collection.set(new_collections[0].collection_id)
        else:
            selected_collection.set(None)

    @reactive.effect
    def update_collections():
        if opensearch_status.get():
            fetch_collections()
        else:
            collections.set(CollectionsData(collections={}, loading=False))

    prompter_server(
        "prompter",
        client,
        selected_collection,
        collections,
        opensearch_status,
        ollama_status,
        collection_selector_server,
    )


shiny_app = App(app_ui, server)

routes = [
    Route("/files/{collection_id}/{doc_type}/{doc_id}", endpoint=serve_files),
    Mount("/", app=shiny_app),
]


app = Starlette(routes=routes)
