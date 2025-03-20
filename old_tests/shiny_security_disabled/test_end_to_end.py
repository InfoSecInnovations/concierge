from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from shiny.run import run_shiny_app
import pytest
from shiny.playwright import controller
from concierge_backend_lib.document_collections import (
    create_collection,
    delete_collection,
)


@pytest.fixture(scope="module")
def no_timeout_app():
    sa: ShinyAppProc = run_shiny_app(
        "./concierge_shiny/app.py",
        wait_for_start=True,
        timeout_secs=300,
    )
    return sa


timeout = 30000


def test_sidebar(page: Page, no_timeout_app: ShinyAppProc):
    page.goto(no_timeout_app.url)
    nav = controller.NavsetPillList(page, "concierge_nav")
    nav.expect_nav_titles(
        ["Home", "Prompter", "Collection Management"], timeout=timeout
    )


def test_prompter_without_collection(page: Page, no_timeout_app: ShinyAppProc):
    page.goto(no_timeout_app.url)
    nav = controller.NavsetPillList(page, "concierge_nav")
    nav.expect_nav_titles(
        ["Home", "Prompter", "Collection Management"], timeout=timeout
    )
    nav.set("Prompter")
    prompter_ui = controller.OutputUi(page, "prompter-prompter_ui")
    # text prompting use to create a collection should appear
    prompter_ui.expect.to_have_text(
        "Please create a collection and ingest some documents into it first!"
    )
    # once that state has been reached, we check that there is no chat
    chat = controller.Chat(page, "prompter-prompter_chat")
    chat.expect.to_have_count(0, timeout=timeout)
    # TODO: check for prompter options selectors


async def test_prompter_with_collection(page: Page, no_timeout_app: ShinyAppProc):
    collection_id = await create_collection(None, "collection_1")
    page.goto(no_timeout_app.url)
    nav = controller.NavsetPillList(page, "concierge_nav")
    nav.expect_nav_titles(
        ["Home", "Prompter", "Collection Management"], timeout=timeout
    )
    nav.set("Prompter")
    chat = controller.Chat(page, "prompter-prompter_chat")
    chat.expect.to_have_count(1, timeout=timeout)
    # TODO: check for prompter options selectors
    await delete_collection(None, collection_id)
