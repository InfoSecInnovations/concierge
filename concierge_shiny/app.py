from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from home import home_ui
from prompter import prompter_ui, prompter_server
from collection_management import collection_management_ui, collection_management_server
import shinyswatch
from components import status_ui, status_server
from opensearch_binary import serve_binary
from oauth2 import auth_callback, refresh, logout, get_keycloak_client
from starlette.applications import Starlette
from starlette.routing import Mount, Route
import os
import dotenv
from auth import get_auth_tokens
from functions import set_collections
from concierge_util import load_config
from concierge_backend_lib.opensearch import get_client

dotenv.load_dotenv()

app_ui = ui.page_auto(
    ui.output_ui("concierge_main"),
    theme=shinyswatch.theme.pulse,
)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = (
    "1"  # this is to use keycloak in localhost, TODO: be able to toggle
)


def server(input: Inputs, output: Outputs, session: Session):
    shinyswatch.theme_picker_server()
    config = load_config()
    token, claims = get_auth_tokens(session, config)
    if config["auth"] and not token:
        return
    if config["auth"]:
        keycloak_client = get_keycloak_client()
        print(keycloak_client.uma_permissions(token["access_token"]))
        print(
            keycloak_client.uma_permissions(
                token["access_token"], "41d7f2f6-58b0-4010-b1eb-a19406e619d9#read"
            )
        )
        print(
            keycloak_client.has_uma_access(
                token["access_token"], "41d7f2f6-58b0-4010-b1eb-a19406e619d9#read"
            )
        )
        print(
            keycloak_client.has_uma_access(
                token["access_token"], "ee9c0267-85cf-4471-9107-6897ebc98521#read"
            )
        )
    else:
        keycloak_client = None
    opensearch_status = reactive.value(False)
    ollama_status = reactive.value(False)
    selected_collection = reactive.value("")
    collections = reactive.value([])
    client = get_client()

    @render.ui
    def concierge_main():
        nav_items = [
            ui.nav_panel("Home", home_ui("home")),
            ui.nav_panel("Prompter", prompter_ui("prompter")),
            ui.nav_panel(
                "Collection Management",
                collection_management_ui("collection_management"),
            ),
        ]
        if token:
            nav_items.append(
                ui.nav_control(
                    ui.input_action_button("openid_logout", "Log Out", class_="my-3")
                )
            )
        nav_items.append(
            ui.nav_control(status_ui("status_widget"), shinyswatch.theme_picker_ui())
        )
        return ui.navset_pill_list(
            *nav_items,
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
    status = status_server("status_widget")

    @reactive.effect
    def update_collections():
        if opensearch_status.get():
            set_collections(config, claims, client, collections)
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
    Route("/callback", endpoint=auth_callback),
    Route("/refresh", endpoint=refresh),
    Route("/logout", endpoint=logout),
    Route("/files/{collection_name}/{doc_type}/{doc_id}", endpoint=serve_binary),
    Mount("/", app=shiny_app),
]


app = Starlette(routes=routes)
