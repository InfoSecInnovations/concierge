from shiny import module, reactive, ui, req, render, Inputs, Outputs, Session
from shiny._utils import rand_hex
from concierge_backend_lib.status import check_ollama, check_opensearch
from concierge_backend_lib.document_collections import (
    create_collection,
    get_collections,
    CollectionExistsError,
)
from isi_util.async_single import asyncify
import os
from functions import format_collection_name
from concierge_backend_lib.authorization import auth_enabled
from collections_data import CollectionsData
from auth import WebAppAsyncTokenTaskRunner

# --------
# COLLECTION SELECTOR
# --------


@module.ui
def collection_selector_ui():
    return [ui.output_ui("collection_selector")]


@module.server
def collection_selector_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    selected_collection,
    collections,
    user_info,
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
            choices={
                collection["_id"]: format_collection_name(collection, user_info.get())
                for collection in collections.get().collections
            },
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
def collection_create_ui(show_toggle):
    elements = [
        text_input_enter_ui("new_collection", "New Collection", COLLECTION_PLACEHOLDER)
    ]
    if show_toggle:
        elements.append(ui.input_checkbox("toggle_shared", "Shared Collection"))
    return elements


@module.server
def collection_create_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    selected_collection,
    collections,
    task_runner: WebAppAsyncTokenTaskRunner,
    permissions,
):
    creating = reactive.value(False)
    new_collection_name = text_input_enter_server("new_collection", creating)

    @reactive.extended_task
    async def create_concierge_collection(collection_name, location):
        async def do_create(token):
            collection_id = await create_collection(
                token["access_token"],
                collection_name,
                location,
            )
            new_collections = await get_collections(token["access_token"])
            return (collection_id, new_collections)

        return await task_runner.run_async_task(do_create)

    @reactive.effect
    def create_collection_effect():
        try:
            collection_id, new_collections = create_concierge_collection.result()
            collections.set(
                CollectionsData(
                    collections=new_collections,
                    loading=False,
                )
            )
            selected_collection.set(collection_id)
        except CollectionExistsError:
            ui.notification_show(
                "Collection with this name already exists", type="error"
            )
        creating.set(False)

    @reactive.effect
    @reactive.event(new_collection_name, ignore_none=True, ignore_init=True)
    def on_create():
        req(new_collection_name())
        new_name = new_collection_name()
        if not new_name:
            return
        if not auth_enabled:
            location = None
        else:
            perms = permissions.get()
            if "collection:private:create" not in perms:
                location = "shared"
            elif "collection:shared:create" not in perms:
                location = "private"
            else:
                location = "shared" if input.toggle_shared() else "private"
        creating.set(True)
        create_concierge_collection(new_name, location)
