from shiny import module, reactive, ui, render, Inputs, Outputs, Session
from shiny._utils import rand_hex

@module.ui
def text_list_ui():
    return ui.output_ui("text_list")


@module.server
def text_list_server(input: Inputs, output: Outputs, session: Session, clear_trigger):
    input_ids = reactive.value([f"input_{rand_hex(4)}"])
    container_id = module.resolve_id("input_list_container")
    list_id = module.resolve_id("input_list")
    init = reactive.value(0)

    @render.ui
    # this is a bit of a hack to make the UI only render once
    # we can't rely on the module UI to display at the same time the server is called, so we use this instead
    @reactive.event(init, ignore_none=False)
    def text_list():
        return ui.div(
            ui.div(
                *[ui.input_text(input_id, None) for input_id in input_ids.get()],
                id=list_id,
            ),
            id=container_id,
        )

    @reactive.calc
    def input_values():
        return [input[id]() for id in input_ids.get()]

    @reactive.effect
    @reactive.event(input_values, ignore_none=False, ignore_init=False)
    def handle_inputs():
        # if IDs were deleted, remake the whole input list
        if not len(input_ids.get()):
            ui.remove_ui(selector=f"#{container_id} *", multiple=True, immediate=True)
            ui.insert_ui(
                ui.div(id=list_id), selector=f"#{container_id}", immediate=True
            )

        filled = []
        empty = []
        for id in input_ids.get():
            if input[id]():
                filled.append(id)
            else:
                empty.append(id)
        # if there's already one empty input we're good to go
        if len(empty) == 1:
            return

        # in any other situation we should take the filled elements and remove the others
        idx = rand_hex(4)
        new_id = f"input_{idx}"
        with reactive.isolate():
            input_ids.set([*filled, new_id])
            for id in empty:
                del input[id]
                ui.remove_ui(
                    selector=f"div:has(> #{module.resolve_id(id)})", immediate=True
                )
            ui.insert_ui(ui.input_text(new_id, None), selector=f"#{list_id}")

    @reactive.effect
    @reactive.event(clear_trigger, ignore_init=True)
    def clear_inputs():
        for id in input_ids.get():
            del input[id]
        input_ids.set([])

    return input_values