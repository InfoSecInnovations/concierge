from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from shiny.pytest import create_app_fixture

app = create_app_fixture("./concierge_shiny/app.py")


def test_basic_app(page: Page, app: ShinyAppProc):
    page.goto(app.url)
    # nav = controller.NavsetPillList(page, "navbar")
    # nav.expect_nav_titles(["Home", "Prompter", "Collection Management"])
