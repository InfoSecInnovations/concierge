# Same test as app.py but with more basic UI elements

from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from asyncio import sleep

app_ui = ui.page_auto(ui.output_ui("nav"))


def server(input: Inputs, output: Outputs, session: Session):
    conditional_page = reactive.value(False)

    @reactive.extended_task
    async def toggle_page_state():
        await sleep(1)
        return True

    @render.ui
    def nav():
        # switch the commenting on the 2 lines below to fix the error
        # value = conditional_page.get()
        value = toggle_page_state.result()
        if value:
            return ui.markdown("Enabled")
        return ui.markdown("Disabled")

    @reactive.effect
    def on_toggle():
        conditional_page.set(toggle_page_state.result())

    @reactive.effect
    def startup():
        toggle_page_state()


app = App(app_ui, server)
