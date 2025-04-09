from shiny import module, reactive, ui, Inputs, Outputs, Session
import os

@module.ui
def text_input_enter_ui(label, placeholder):
    id_input = module.resolve_id("text_input_enter")
    id_enter = module.resolve_id("enter")
    return [
        ui.div(
            ui.div(
                ui.tags.input(
                    id=id_input,
                    type="text",
                    class_="form-control",
                    placeholder=placeholder,
                    aria_label=placeholder,
                ),
                ui.input_task_button(id="text_input_submit", label=label),
                class_="input-group",
            ),
            {
                "class": "text-input-enter",
                # We'll use this ID in the JavaScript to report the value
                # so the Shiny app can call `input.enter()` inside the module
                "data-enter-id": id_enter,
            },
        ),
        ui.include_js(
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "js", "text_input_enter.js")
            ),
            method="inline",
        ),
    ]


@module.server
def text_input_enter_server(
    input: Inputs, output: Outputs, session: Session, processing
):
    # We're going to indepedently set the value when either
    # * the submit button is pressed
    # * the Enter button is pressed
    value = reactive.value(None)

    @reactive.effect
    @reactive.event(input.text_input_submit)
    def on_click_submit():
        value.set(input.text_input_enter())

    @reactive.effect
    @reactive.event(input.enter)
    def on_press_enter():
        # input.enter() reports the value of the text input field
        # because it's easy for users to press Enter quickly while typing
        # before input.text_input_enter() has had a chance to update
        value.set(input.enter())

    @reactive.effect
    @reactive.event(processing)
    def on_processing_change():
        ui.update_task_button(
            id="text_input_submit", state="busy" if processing.get() else "ready"
        )
        # clearing the value means that you can resubmit the same text and it will trigger the reactivity again
        if not processing.get():
            value.set(None)

    return value