from shiny import module, reactive, ui, req, render, Inputs, Outputs, Session
from shiny._utils import rand_hex
from concierge_backend_lib.status import check_ollama, check_opensearch
from concierge_backend_lib.opensearch import get_collections, ensure_collection
from isi_util.async_single import asyncify
import os
from markdown_renderer import md

# --------
# COLLECTION SELECTOR
# --------


@module.ui
def collection_selector_ui():
    return [ui.output_ui("collection_selector")]


@module.server
def collection_selector_server(
    input: Inputs, output: Outputs, session: Session, selected_collection, collections
):
    @render.ui
    def collection_selector():
        return ui.output_ui("select_dropdown")

    @render.ui
    def select_dropdown():
        req(collections.get())
        return ui.input_select(
            id="internal_selected_collection",
            label="Select Collection",
            choices=collections.get(),
            selected=selected_collection.get(),
        )

    @reactive.effect
    def update_selection():
        selected_collection.set(input.internal_selected_collection())


# --------
# STATUS
# --------


@module.ui
def status_ui():
    return ui.output_ui("status_widget")


@module.server
def status_server(input: Inputs, output: Outputs, session: Session):
    opensearch_status = reactive.value(False)
    ollama_status = reactive.value(False)

    @reactive.extended_task
    async def get_ollama_status():
        return await asyncify(check_ollama)

    @reactive.extended_task
    async def get_opensearch_status():
        return await asyncify(check_opensearch)

    @reactive.effect
    def set_ollama_status():
        ollama_status.set(get_ollama_status.result())

    @reactive.effect
    def set_opensearch_status():
        opensearch_status.set(get_opensearch_status.result())

    @reactive.effect
    def poll():
        reactive.invalidate_later(10)
        get_ollama_status()
        get_opensearch_status()

    @render.ui
    def status_widget():
        return ui.card(
            ui.markdown(f"{'🟢' if opensearch_status.get() else '🔴'} OpenSearch"),
            ui.markdown(f"{'🟢' if ollama_status.get() else '🔴'} Ollama"),
        )

    @reactive.calc
    def result():
        return {"opensearch": opensearch_status.get(), "ollama": ollama_status.get()}

    return result


# --------
# TEXT INPUT LIST
# --------


@module.ui
def text_list_ui():
    container_id = module.resolve_id("input_list_container")
    list_id = module.resolve_id("input_list")
    return ui.div(ui.div(ui.input_text("input_0", None), id=list_id), id=container_id)


@module.server
def text_list_server(input: Inputs, output: Outputs, session: Session, clear_trigger):
    input_ids = reactive.value(["input_0"])
    container_id = module.resolve_id("input_list_container")
    list_id = module.resolve_id("input_list")

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

        # if there's already an empty input we don't need more
        if not all([len(x) > 0 for x in input_values()]):
            return

        # insert new ID and corresponding element if all existing ones have values
        idx = rand_hex(4)
        new_id = f"input_{idx}"
        input_ids.set([*input_ids.get(), new_id])
        ui.insert_ui(ui.input_text(new_id, None), selector=f"#{list_id}")

    @reactive.effect
    @reactive.event(clear_trigger, ignore_init=True)
    def clear_inputs():
        for id in input_ids.get():
            del input[id]
        input_ids.set([])

    return input_values


# --------
# TEXT INPUT ENTER
# --------


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
                os.path.join(os.path.dirname(__file__), "js", "text_input_enter.js")
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


# --------
# COLLECTION CREATOR
# --------

COLLECTION_PLACEHOLDER = "new_collection_name"


@module.ui
def collection_create_ui():
    return [
        text_input_enter_ui("new_collection", "New Collection", COLLECTION_PLACEHOLDER),
        ui.markdown(
            'Hint: Collection names must be lowercase and may not begin with underscores or hyphens. See [here](https://opensearch.org/docs/latest/api-reference/index-apis/create-index/#index-naming-restrictions){target="_blank"} for the full list of restrictions.',
            render_func=md.render,
        ),
    ]


@module.server
def collection_create_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    selected_collection,
    collections,
    client,
):
    creating = reactive.value(False)
    new_collection_name = text_input_enter_server("new_collection", creating)

    @reactive.extended_task
    async def create_collection(collection_name):
        await asyncify(ensure_collection, client, collection_name)
        selected_collection.set(collection_name)
        print(f"created collection {collection_name}")
        collections.set(await asyncify(get_collections, client))
        creating.set(False)

    @reactive.effect
    @reactive.event(new_collection_name, ignore_none=True, ignore_init=True)
    def on_create():
        req(new_collection_name())
        new_name = new_collection_name()
        if not new_name:
            return
        creating.set(True)
        create_collection(new_name)
