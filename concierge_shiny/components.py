from shiny import module, reactive, ui, req, render, Inputs, Outputs, Session
from concierge_backend_lib.collections import get_collections, init_collection
from concierge_backend_lib.status import get_status
from util.async_single import asyncify

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
def collection_create_server(input: Inputs, output: Outputs, session: Session, selected_collection, collections):
    
    @reactive.effect
    @reactive.event(input.create_collection, ignore_none=False, ignore_init=True)
    def create_new_collection():
        req(input.new_collection_name())
        new_name = input.new_collection_name()
        init_collection(new_name)
        print(f"created collection {new_name}")
        collections.set(get_collections())
        selected_collection.set(new_name)
        ui.update_text(id="new_collection_name", label=None, value="", placeholder=COLLECTION_PLACEHOLDER)

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

@module.ui
def status_ui():
    return ui.output_ui("status_widget")

@module.server
def status_server(input: Inputs, output: Outputs, session: Session):

    milvus_status = reactive.value(False)
    ollama_status = reactive.value(False)

    @reactive.extended_task
    async def get_requirements_status():
        return await asyncify(get_status)

    @reactive.effect
    def set_requirements_status():
        status = get_requirements_status.result()
        milvus_status.set(status["milvus"])
        ollama_status.set(status["ollama"])

    @reactive.effect
    def poll():
        reactive.invalidate_later(10)
        get_requirements_status()

    @render.ui
    def status_widget():
        return ui.card(
            ui.markdown(f"Milvus: {'Up' if milvus_status.get() else 'Down'}"),
            ui.markdown(f"Ollama: {'Up' if ollama_status.get() else 'Down'}")
        )
    
    @reactive.calc
    def result():
        return { "milvus": milvus_status.get(), "ollama": ollama_status.get()}
    
    return result