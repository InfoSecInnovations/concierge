# This shows how it's possible to break the theme picker by disabling and enabling it
# The documentation suggests that maybe you shouldn't do this, so the solution is to always have it in the app

from shiny import App, ui, Inputs, Outputs, Session, reactive, render
import shinyswatch

app_ui = ui.page_auto(
    ui.markdown("# Hello World!"),
    ui.card(
        ui.card_header("This is some UI"),
        ui.card_body(
            "This is some more UI",
            ui.input_action_button("test", "This isn't a real button"),
        ),
        ui.card_footer("And this too"),
    ),
    ui.output_ui("conditional_ui"),
    ui.input_action_button("enable_picker", "Toggle picker"),
    theme=shinyswatch.theme.darkly,
)


def server(input: Inputs, output: Outputs, session: Session):
    picker_enabled = reactive.value(False)
    shinyswatch.theme_picker_server()

    @render.ui
    def conditional_ui():
        if picker_enabled.get():
            return shinyswatch.theme_picker_ui()
        return ui.markdown("No picker")

    @reactive.effect
    @reactive.event(input.enable_picker)
    def toggle_picker():
        picker_enabled.set(not picker_enabled.get())


app = App(app_ui, server)
