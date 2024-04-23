from shiny import App, ui, Inputs, Outputs, Session, render, reactive

app_ui = ui.page_auto(
    ui.markdown("# Testing"),
    ui.div(
        ui.input_text("test_0", "Test 0"),
        id="input_test_list"
    )
)

def server(input: Inputs, output: Outputs, session: Session):
    
    test_ids = reactive.value(["test_0"])

    
    @reactive.calc
    def test_values():
        return [input[id]() for id in test_ids.get()]

    @reactive.effect
    @reactive.event(test_values)
    def _():
        if not all([len(x) > 0 for x in test_values()]):
            return

        idx = len(test_values())
        new_id = f"test_{idx}"
        
        test_ids.set([*test_ids.get(), new_id])
        
        ui.insert_ui(
            ui.input_text(new_id, f"Test {idx}"),
            selector="#input_test_list"
        )

app = App(app_ui, server)