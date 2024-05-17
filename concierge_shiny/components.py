from shiny import module, reactive, ui, req, render, Inputs, Outputs, Session
from concierge_backend_lib.status import check_ollama, check_opensearch
from concierge_backend_lib.opensearch import get_indices, ensure_index
from util.async_single import asyncify
import uuid

# --------
# COLLECTION CREATOR
# --------

COLLECTION_PLACEHOLDER = "new_collection_name"

@module.ui
def collection_create_ui():
    return [
        ui.layout_columns(
            ui.input_text(id="new_collection_name", label=None, placeholder=COLLECTION_PLACEHOLDER),
            ui.input_action_button(id="create_collection", label="New Collection"),
            col_widths=[8, 4]
        ),
        ui.markdown("Hint: Collection names must contain only letters, numbers, or underscores.")
    ]

@module.server
def collection_create_server(input: Inputs, output: Outputs, session: Session, selected_collection, collections, client):
    
    @reactive.effect
    @reactive.event(input.create_collection, ignore_none=False, ignore_init=True)
    def create_new_collection():
        req(input.new_collection_name())
        new_name = input.new_collection_name()
        ensure_index(client, new_name)
        print(f"created collection {new_name}")
        collections.set(get_indices(client))
        selected_collection.set(new_name)
        ui.update_text(id="new_collection_name", label=None, value="", placeholder=COLLECTION_PLACEHOLDER)

# --------
# COLLECTION SELECTOR
# --------

@module.ui
def collection_selector_ui():
    return [
        ui.output_ui("collection_selector")
    ]

@module.server
def collection_selector_server(input: Inputs, output: Outputs, session: Session, selected_collection, collections):

    @render.ui
    def collection_selector():
        return ui.output_ui("select_dropdown")
    
    @render.ui
    def select_dropdown():
        req(collections.get())
        return ui.input_select(id="internal_selected_collection", label="Select Collection", choices=collections.get(), selected=selected_collection.get())
    
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
            ui.markdown(f"{'🟢' if ollama_status.get() else '🔴'} Ollama")
        )
    
    @reactive.calc
    def result():
        return { "opensearch": opensearch_status.get(), "ollama": ollama_status.get()}
    
    return result

# --------
# TEXT INPUT LIST
# --------

@module.ui
def text_list_ui():
    container_id = module.resolve_id("input_list_container")
    list_id = module.resolve_id("input_list")
    return ui.div(
        ui.div(
            ui.input_text("input_0", None),
            id=list_id), 
        id=container_id
    )

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
                ui.div(id=list_id),
                selector=f"#{container_id}",
                immediate=True
            )

        # if there's already an empty input we don't need more
        if not all([len(x) > 0 for x in input_values()]):
            return

        # insert new ID and corresponding element if all existing ones have values
        idx = uuid.uuid4().int
        new_id = f"input_{idx}"       
        input_ids.set([*input_ids.get(), new_id])
        ui.insert_ui(
            ui.input_text(new_id, None),
            selector=f"#{list_id}"
        )

    @reactive.effect
    @reactive.event(clear_trigger, ignore_init=True)
    def clear_inputs():
        for id in input_ids.get():
            del input[id]   
        input_ids.set([])

    return input_values