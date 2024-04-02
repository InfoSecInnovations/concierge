from shiny import module, reactive, ui, req, render, Inputs, Outputs, Session
from concierge_backend_lib.collections import get_collections, init_collection

@module.ui
def collection_create_ui():
    return [
        ui.input_text(id="new_collection_name", label="Collection Name"),
        ui.input_action_button(id="create_collection", label="Create Collection"),
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

@module.ui
def collection_selector_ui():
    return [
        ui.output_ui("collection_selector")
    ]

@module.server
def collection_selector_server(input: Inputs, output: Outputs, session: Session, selected_collection, collections):

    collection_create_server("create_collection", selected_collection, collections)

    @render.ui
    def collection_selector():
        req(collections.get())
        return ui.TagList(
            ui.input_selectize(id="internal_selected_collection", label="Select Collection", choices=collections.get(), selected=selected_collection.get()),
            collection_create_ui("create_collection")
        )
    
    @reactive.effect
    def update_selection():
        selected_collection.set(input.internal_selected_collection())