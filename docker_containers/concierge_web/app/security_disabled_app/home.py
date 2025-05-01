from shiny import ui, Inputs, Outputs, Session, render, module
from ..common.markdown_renderer import md
from ..common.home_texts import TITLE, QUICKSTART, TIPS, CONTRIBUTING


@module.ui
def home_ui():
    return ui.output_ui("home_text")


@module.server
def home_server(input: Inputs, output: Outputs, session: Session):
    @render.ui
    def home_text():
        return ui.markdown(
            "\n".join([TITLE, QUICKSTART, TIPS, CONTRIBUTING]), render_func=md.render
        )
