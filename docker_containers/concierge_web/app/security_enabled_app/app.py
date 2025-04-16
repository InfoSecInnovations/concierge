import os
from shiny import ui, Inputs, Outputs, Session, reactive, App, render
import shinyswatch
from .collections_data import CollectionsData
from concierge_api_client import ConciergeAuthorizationClient
from concierge_keycloak import get_keycloak_client
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from .app_login import app as app_login
from .oauth2 import auth_callback, refresh, logout
from .auth import get_auth_token
import ssl
from ..common.status import status_ui, status_server
from .home import home_ui, home_server
from ..common.collection_management_ui import collection_management_ui
from .collection_management import collection_management_server
from .files_route import serve_files

API_URL = "http://127.0.0.1:8000/" # TODO: get this from the environment

app_ui = ui.page_auto(
    ui.output_ui("script_output"),
    ui.output_ui("concierge_main"),
    theme=shinyswatch.theme.pulse,
)

# we're only able to run HTTP in VSCode so we need to allow Oauthlib to use HTTP if we're in the VSCode environment
if os.getenv("VSCODE_INJECTION") == "1":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

def server(input: Inputs, output: Outputs, session: Session):
    shinyswatch.theme_picker_server()
    token = get_auth_token(session)
    if not token:
        return
    client = ConciergeAuthorizationClient(server_url=API_URL, token=token, keycloak_client=get_keycloak_client(), verify=ssl.create_default_context(cafile=os.getenv("ROOT_CA")))
    opensearch_status = reactive.value(False)
    ollama_status = reactive.value(False)
    selected_collection = reactive.value("")
    collections = reactive.value(CollectionsData(loading=True))
    user_info = reactive.value(None)
    permissions: reactive.Value[set] = reactive.value(set())

    @reactive.extended_task
    async def get_info():
        return await client.get_user_info()

    @reactive.effect
    def get_info_effect():
        info = get_info.result()
        user_info.set(info)

    get_info()

    @reactive.extended_task
    async def get_permissions():
        return await client.get_permissions()

    @reactive.effect
    def get_permissions_effect():
        permissions_value = get_permissions.result()
        permissions.set(permissions_value)

    get_permissions()

    @reactive.calc
    def nav_items():
        perms = permissions.get()
        items = [ui.nav_panel("Home", home_ui("home"))]
        if "collection:private:create" in perms or "collection:shared:create" in perms or "update" in perms or "delete" in perms:
            items.append(ui.nav_panel("Collection Management", collection_management_ui("collection_management")))
        items.append(
            ui.nav_control(
                ui.input_action_button("openid_logout", "Log Out", class_="my-3")
            )
        )
        return items

    @render.ui
    def concierge_main():
        return ui.navset_pill_list(
            *nav_items(),
            ui.nav_control(status_ui("status_widget"), shinyswatch.theme_picker_ui()),
            id="concierge_nav",
        )
    
    status = status_server("status_widget", client.ollama_status, client.opensearch_status)

    home_server("home", user_info)
    collection_management_server("collection_management", client, selected_collection, collections, opensearch_status, user_info, permissions)

    @reactive.effect
    def update_status():
        current_status = status()
        opensearch_status.set(current_status["opensearch"])
        ollama_status.set(current_status["ollama"])

    @reactive.extended_task
    async def fetch_collections():
        return await client.get_collections()

    @reactive.effect
    def fetch_collections_effect():
        new_collections = fetch_collections.result()
        collections.set(CollectionsData(collections=new_collections, loading=False))
        if len(new_collections):
            selected_collection.set(new_collections[0].collection_id)
        else:
            selected_collection.set(None)

    @reactive.effect
    def update_collections():
        if opensearch_status.get():
            fetch_collections()
        else:
            collections.set(CollectionsData(collections=[], loading=False))

shiny_app = App(app_ui, server)

routes = [
    Route("/callback", endpoint=auth_callback),
    Route("/refresh", endpoint=refresh),
    Route("/logout", endpoint=logout),
    Route("/files/{collection_id}/{doc_type}/{doc_id}", endpoint=serve_files),
    Mount("/login", app=app_login),
    Mount("/", app=shiny_app),
]


app = Starlette(routes=routes)