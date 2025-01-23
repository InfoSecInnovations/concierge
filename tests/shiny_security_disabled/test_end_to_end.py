from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from shiny.run import run_shiny_app
import pytest
from shiny.playwright import controller

collection_ids = []


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
