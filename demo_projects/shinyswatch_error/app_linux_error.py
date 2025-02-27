# trying to reproduce the shinyswatch error that only happens on Linux
# the code below is producing the error even on Windows

from shiny import App, ui, Inputs, Outputs, Session, reactive, render
import shinyswatch
import asyncio
import random

MAX_UPDATES = 3  # set this in range 1-3 to see the error

app_ui = ui.page_auto(
    ui.output_ui("main_page"),
    ui.input_action_button("change_nav", "Change Nav"),
    theme=shinyswatch.theme.darkly,
)


def server(input: Inputs, output: Outputs, session: Session):
    nav_state = reactive.value(random.randint(0, 10))
    update_count = 0
    shinyswatch.theme_picker_server()

    @reactive.extended_task
    async def update_state(current_state):
        await asyncio.sleep(0.3)
        nonlocal update_count
        update_count += 1
        return current_state + 1

    @reactive.effect
    def on_updated():
        nav_state.set(update_state.result())

    @reactive.calc
    def nav_items():
        dynamic_items = [
            ui.nav_panel(f"Page{i}", ui.markdown(f"# Page{i}"))
            for i in range(nav_state.get())
        ]
        return dynamic_items

    @render.ui
    def main_page():
        print("main")
        return ui.navset_pill_list(
            *nav_items(), ui.nav_control(shinyswatch.theme_picker_ui())
        )

    @reactive.effect
    def startup():
        state = nav_state.get()
        if update_count < MAX_UPDATES:
            update_state(state)


app = App(app_ui, server)
