from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from home import home_ui, home_server
from prompter import prompter_ui, prompter_server
from collection_management import collection_management_ui, collection_management_server
import shinyswatch
from components import status_ui, status_server
from opensearch_binary import serve_binary
from oauth2 import auth_callback, refresh, logout
from starlette.applications import Starlette
from starlette.routing import Mount, Route
import os
from auth import get_task_runner
from collections_data import CollectionsData
from concierge_backend_lib.authentication import get_token_info
from concierge_backend_lib.authorization import auth_enabled, list_permissions
from concierge_backend_lib.document_collections import get_collections
from functions import has_edit_access, has_read_access
from app_login import app as app_login
from concierge_scripts.load_dotenv import load_env

compose_path = os.path.join(os.getcwd(), "bun_installer", "docker_compose")
load_env()

app_ui = ui.page_auto(
    ui.output_ui("script_output"),
    ui.output_ui("concierge_main"),
    theme=shinyswatch.theme.pulse,
)

# we're only able to run HTTP in VSCode so we need to allow Oauthlib to use HTTP if we're in the VSCode environment
if os.getenv("VSCODE_INJECTION") == "1":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def server(input: Inputs, output: Outputs, session: Session):
    user_info = reactive.value(None)
    permissions = reactive.value(None)
    shinyswatch.theme_picker_server()
    task_runner = get_task_runner(session)
    auth_is_enabled = auth_enabled()
    if auth_is_enabled and not task_runner:
        return
    if auth_is_enabled:

        @reactive.extended_task
        async def get_info():
            async def do_get_info(token):
                return await get_token_info(token["access_token"])

            return await task_runner.run_async_task(do_get_info)

        @reactive.effect
        def get_info_effect():
            info = get_info.result()
            user_info.set(info)

        get_info()

        @reactive.extended_task
        async def get_permissions():
            async def do_get_permissions(token):
                return await list_permissions(token["access_token"])

            return await task_runner.run_async_task(do_get_permissions)

        @reactive.effect
        def get_permissions_effect():
            permissions_value = get_permissions.result()
            permissions.set(permissions_value)

        get_permissions()

    opensearch_status = reactive.value(False)
    ollama_status = reactive.value(False)
    selected_collection = reactive.value("")
    collections = reactive.value(CollectionsData(collections=[], loading=True))
    read_access = reactive.value(False)
    edit_access = reactive.value(False)
    # rerender_trigger = reactive.value(0)  # this is an awful hack, see below

    @reactive.extended_task
    async def get_read_access():
        return await has_read_access(task_runner)

    @reactive.extended_task
    async def get_edit_access(permissions):
        return await has_edit_access(permissions, task_runner)

    @reactive.effect
    def on_get_read_access():
        read_access.set(get_read_access.result())

    @reactive.effect
    def on_get_edit_access():
        edit_access.set(get_edit_access.result())

    # the 3 functions below are part of the awful hack
    # we're running into a very weird issue where the shinyswatch theme picker error only appears within a set range of UI refreshes
    # we just trigger a bunch more to make the error go away, it still pops up briefly but this is better than nothing
    # we're awaiting a proper fix from the Shiny team
    # @reactive.extended_task
    # async def rerender(trigger_value):
    #     await asyncio.sleep(0.2)
    #     return trigger_value + 1

    # @reactive.effect
    # def on_rerender():
    #     rerender_trigger.set(rerender.result())

    # @reactive.effect
    # def loop_rerender():
    #     t = rerender_trigger.get()
    #     if t <= 6:
    #         rerender(t)

    @reactive.calc
    def nav_items():
        # _ = rerender_trigger.get()  # this is a very hacky hack to try to trigger a rerender until the shinyswatch error goes away
        items = [ui.nav_panel("Home", home_ui("home"))]
        if not auth_is_enabled or read_access.get():
            items.append(ui.nav_panel("Prompter", prompter_ui("prompter")))
        if not auth_is_enabled or edit_access.get():
            items.append(
                ui.nav_panel(
                    "Collection Management",
                    collection_management_ui("collection_management"),
                )
            )
        if auth_is_enabled:
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

    home_server("home", permissions, user_info, task_runner)

    prompter_server(
        "prompter",
        selected_collection,
        collections,
        opensearch_status,
        ollama_status,
        task_runner,
        user_info,
        permissions,
    )
    collection_management_server(
        "collection_management",
        selected_collection,
        collections,
        opensearch_status,
        task_runner,
        user_info,
        permissions,
    )
    status = status_server("status_widget")

    @reactive.extended_task
    async def fetch_collections():
        async def do_fetch_collections(token):
            return await get_collections(token["access_token"])

        return await task_runner.run_async_task(do_fetch_collections)

    @reactive.effect
    def fetch_collections_effect():
        new_collections = fetch_collections.result()
        collections.set(CollectionsData(collections=new_collections, loading=False))
        if len(new_collections):
            selected_collection.set(new_collections[0]["_id"])
        else:
            selected_collection.set(None)

    @reactive.effect
    def update_collections():
        if opensearch_status.get():
            fetch_collections()
        else:
            collections.set(CollectionsData(collections=[], loading=False))

    @reactive.effect
    def update_status():
        current_status = status()
        opensearch_status.set(current_status["opensearch"])
        ollama_status.set(current_status["ollama"])

    @reactive.effect
    @reactive.event(permissions, ignore_init=True)
    def update_access():
        get_read_access()
        get_edit_access(permissions.get())
        # rerender(1)

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
    Route("/files/{collection_id}/{doc_type}/{doc_id}", endpoint=serve_binary),
    Mount("/login", app=app_login),
    Mount("/", app=shiny_app),
]


app = Starlette(routes=routes)
