from shiny import ui, Inputs, Outputs, Session, render, module, reactive
from ..common.markdown_renderer import md
from ..common.home_texts import TITLE, QUICKSTART, TIPS, CONTRIBUTING, LOADING_API


@module.ui
def home_ui():
    return ui.output_ui("home_text")


@module.server
def home_server(
    input: Inputs, output: Outputs, session: Session, api_status: reactive.Value
):
    @render.ui
    def home_text():
        contents = [TITLE]
        if api_status.get():
            contents.append(QUICKSTART)
        else:
            contents.append(LOADING_API)
        contents.append(TIPS)
        contents.append(CONTRIBUTING)
        return ui.markdown("\n".join(contents), render_func=md.render)
