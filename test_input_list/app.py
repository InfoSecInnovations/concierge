from shiny import App, ui, Inputs, Outputs, Session, render, reactive

app_ui = ui.page_auto(
    ui.markdown("# Testing"),
    ui.output_ui("output_area")
)

def server(input: Inputs, output: Outputs, session: Session):
    
    values = reactive.value([])

    @render.ui
    def output_area():
        return ui.TagList(
            *[ui.input_text(f"input_test_{index}", "Test", value) for index, value in enumerate(values.get())],
            ui.input_text(f"input_test_{len(values.get())}", "Test")
        )

    @reactive.effect
    def values_backend():
        values_value = values.get()
        changed = False
        for index, url in enumerate(values_value):
            new_url = input[f"input_test_{index}"]()
            if new_url != url:
                values_value[index] = new_url
                changed = True
        new_url = input[f"input_test_{len(values_value)}"]()
        if new_url:
            values_value.append(new_url)
            changed = True
        if changed:
            values.set([*values_value])


app = App(app_ui, server)