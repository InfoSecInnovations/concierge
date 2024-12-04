# It doesn't seem to be intended to combine an extended task result with an output UI
# The app below gives you an error about "an unexpected state of: 'persistent'"
# Having a reactive listen to the extended task and having the UI listen to that fixes the issue
# The error doesn't seem to actually prevent the app from functioning, but we don't want our app throwing errors!

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
        nav_items = [
            ui.nav_panel("Page 1", ui.markdown("This is page 1")),
            ui.nav_panel("Page 2", ui.markdown("This is page 2")),
        ]
        # if you replace this with the conditional_page reactive the error disappears
        if toggle_page_state.result():
            nav_items.append(
                ui.nav_panel(
                    "Conditional Page",
                    ui.markdown("This page was enabled conditionally"),
                )
            )
        return ui.navset_pill_list(*nav_items)

    @reactive.effect
    def on_toggle():
        conditional_page.set(toggle_page_state.result())

    @reactive.effect
    def startup():
        toggle_page_state()


app = App(app_ui, server)
