from shiny import ui, Inputs, Outputs, Session, App, render
from src.app.common.text_input_list import output_list

app_ui = ui.page_auto(output_list("text_list"), ui.output_text("list_value"))


def server(input: Inputs, output: Outputs, session: Session):
    @render.text
    def list_value():
        return input.text_list()


app = App(app_ui, server)
