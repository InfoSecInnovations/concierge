from shiny import ui
import os


def asset(kind: str, name: str):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", kind, name))


def app_assets():
    """The static CSS and JS the whole app needs.

    Included at page level rather than from any panel: the panels are all inside `@render.ui`
    functions that re-run on a collection switch, and toasts are visible from every tab anyway. The
    progress handler in particular has to be registered once, before any toast goes up.
    """
    return ui.TagList(
        ui.include_css(asset("css", "shabti.css"), method="inline"),
        ui.include_js(asset("js", "progress_toast.js"), method="inline"),
    )
