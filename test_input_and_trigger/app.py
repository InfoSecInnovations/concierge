from shiny import App, ui, Inputs, Outputs, Session, render, reactive

app_ui = ui.page_auto(
    ui.markdown("# Testing"),
    ui.output_ui("output_area")
)

def server(input: Inputs, output: Outputs, session: Session):
    
    test_trigger = reactive.value(0)

    @render.ui
    def output_area():
        return ui.TagList(
            ui.input_text("input_test", "Test"),
            ui.markdown(str(test_trigger.get()))
        )

    @reactive.effect
    @reactive.event(input.input_test, ignore_none=False, ignore_init=False)
    def increment_trigger():
        test_trigger.set(test_trigger.get() + 1)

app = App(app_ui, server)