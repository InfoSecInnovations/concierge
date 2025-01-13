# This shows how it's possible to break the theme picker by recreating it

from shiny import App, ui, Inputs, Outputs, Session, reactive, render
import shinyswatch

app_ui = ui.page_auto(
    ui.output_ui("main_page"),
    ui.input_action_button("change_nav", "Change Nav"),
    theme=shinyswatch.theme.darkly,
)


def server(input: Inputs, output: Outputs, session: Session):
    shinyswatch.theme_picker_server()
    nav_state = reactive.value(1)

    @reactive.calc
    def nav_items():
        return [
            ui.nav_panel(f"Page{i}", ui.markdown(f"# Page{i}"))
            for i in range(nav_state.get())
        ]

    @render.ui
    def main_page():
        return ui.navset_pill_list(
            *nav_items(), ui.nav_control(shinyswatch.theme_picker_ui())
        )

    @reactive.effect
    @reactive.event(input.change_nav)
    def change_state():
        nav_state.set(1 if nav_state.get() == 2 else 2)


app = App(app_ui, server)
