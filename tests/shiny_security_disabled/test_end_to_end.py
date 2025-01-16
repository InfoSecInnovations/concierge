from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from shiny.run import run_shiny_app
import pytest


@pytest.fixture(scope="module")
def no_timeout_app():
    sa: ShinyAppProc = run_shiny_app(
        "./concierge_shiny/app.py",
        wait_for_start=True,
        timeout_secs=300,
    )
    return sa


def test_basic_app(page: Page, no_timeout_app: ShinyAppProc):
    page.goto(no_timeout_app.url)
