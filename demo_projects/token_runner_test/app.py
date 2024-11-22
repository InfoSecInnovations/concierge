from shiny import App, ui, Inputs, Outputs, Session, reactive
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from concierge_shiny.oauth2 import auth_callback, refresh, logout
from concierge_backend_lib.authentication import AsyncTokenTaskRunner, get_token_info
from concierge_util import load_config
from concierge_shiny.auth import get_auth_tokens
from concierge_backend_lib.document_collections import get_collections
from isi_util.async_single import asyncify
import asyncio

app_ui = ui.page_auto(
    ui.markdown("# Testing token runner"), ui.output_ui("concierge_main")
)


def server(input: Inputs, output: Outputs, session: Session):
    config = load_config()
    auth_token = get_auth_tokens(session, config)
    if not auth_token:
        return
    token_task_runner = AsyncTokenTaskRunner(auth_token)

    async def get_collections_async(token):
        collections = await asyncify(get_collections, token["access_token"])
        print(collections)

    async def get_user_info_async(token):
        info = await asyncify(get_token_info, token["access_token"])
        print(info)

    @reactive.extended_task
    async def run_tasks():
        print("run tasks")
        for i in range(3):
            # run 10 concurrent tasks using the access token
            await asyncio.gather(
                *[
                    token_task_runner.run_with_token(get_collections_async)
                    for _ in range(5)
                ],
                *[
                    token_task_runner.run_with_token(get_user_info_async)
                    for _ in range(5)
                ],
            )
            print(f"task loop {i} finished")
            if i < 2:
                # if you set the token expiry to 10s, this should make the next batch of tasks require a fresh token
                for j in range(10, 0, -1):
                    print(f"rerunning loop in {j} s")
                    await asyncio.sleep(1)
        print("all tasks run")

    run_tasks()


shiny_app = App(app_ui, server)


routes = [
    Route("/callback", endpoint=auth_callback),
    Route("/refresh", endpoint=refresh),
    Route("/logout", endpoint=logout),
    Mount("/", app=shiny_app),
]


app = Starlette(routes=routes)
