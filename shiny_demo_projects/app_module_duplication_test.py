from shiny import ui, Inputs, Outputs, Session, reactive, App, render, module
from shiny._utils import rand_hex


@module.ui
def test_module_ui():
    return ui.output_ui("view")


@module.server
def test_module_server(input: Inputs, output: Outputs, session: Session):
    module_uuid = rand_hex(6)
    module_value = reactive.Value(0)

    @render.ui
    def view():
        return [
            ui.markdown("Module"),
            ui.input_action_button("module_button", "Increment"),
            ui.output_ui("module_value_output"),
        ]

    @reactive.effect
    def module_reactive():
        print("module reactive")
        print(module_uuid)
        print(module_value.get())

    @reactive.effect
    @reactive.event(input.module_button, ignore_init=True, ignore_none=False)
    def increment():
        module_value.set(module_value.get() + 1)

    @render.ui
    def module_value_output():
        return ui.markdown(f"value: {module_value.get()}")


app_ui = ui.page_auto(ui.output_ui("main"))


def server(input: Inputs, output: Outputs, session: Session):
    @render.ui
    def main():
        return [
            ui.markdown("Hello"),
            ui.input_action_button("test_button", "Refresh module"),
            test_module_ui("test_module"),
        ]

    @reactive.effect()
    @reactive.event(input.test_button, ignore_init=False, ignore_none=False)
    def reactive_server():
        test_module_server("test_module")


app = App(app_ui, server)
