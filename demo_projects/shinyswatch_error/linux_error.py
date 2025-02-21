# trying to reproduce the shinyswatch error that only happens on Linux

from shiny import App, ui, Inputs, Outputs, Session, reactive, render, module
import shinyswatch
import asyncio


@module.ui
def module_ui():
    return [ui.markdown("# Module"), ui.output_ui("module_contents")]


@module.server
def module_server(input: Inputs, output: Outputs, session: Session):
    module_state = reactive.value(1)

    @render.ui
    def module_contents():
        return ui.markdown(f"State: {module_state.get()}")

    @reactive.extended_task
    async def update_state(current_state):
        await asyncio.sleep(0.5)
        return current_state + 1

    @reactive.effect
    def on_updated():
        module_state.set(update_state.result())

    @reactive.effect
    def startup():
        update_state(module_state.get())


app_ui = ui.page_auto(
    ui.output_ui("main_page"),
    ui.input_action_button("change_nav", "Change Nav"),
    theme=shinyswatch.theme.darkly,
)


def server(input: Inputs, output: Outputs, session: Session):
    nav_state = reactive.value(1)
    module_server("sub_module")

    @reactive.extended_task
    async def update_state(current_state):
        await asyncio.sleep(0.3)
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
        return [ui.nav_panel("Module", module_ui("sub_module")), *dynamic_items]

    @render.ui
    def main_page():
        shinyswatch.theme_picker_server()  # this is the workaround that's supposed to fix it
        return ui.navset_pill_list(
            *nav_items(), ui.nav_control(shinyswatch.theme_picker_ui())
        )

    @reactive.effect
    def startup():
        state = nav_state.get()
        if state <= 3:
            update_state(state)


app = App(app_ui, server)
