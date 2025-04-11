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

    @reactive.extended_task
    async def get_info():
        return await client.get_user_info()

    @reactive.effect
    def get_info_effect():
        info = get_info.result()
        user_info.set(info)

    get_info()

    @reactive.calc
    def nav_items():
        items = [ui.nav_panel("Home", home_ui("home"))]
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

shiny_app = App(app_ui, server)

routes = [
    Route("/callback", endpoint=auth_callback),
    Route("/refresh", endpoint=refresh),
    Route("/logout", endpoint=logout),
    Mount("/login", app=app_login),
    Mount("/", app=shiny_app),
]


app = Starlette(routes=routes)