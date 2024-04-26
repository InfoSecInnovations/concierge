from shiny import module, reactive, ui, render, Inputs, Outputs, Session
from components import collection_create_ui, collection_create_server
from concierge_backend_lib.collections import get_collections
from pymilvus import utility

@module.ui
def collection_item_ui():
    return ui.output_ui("collection_view")

@module.server
def collection_item_server(input: Inputs, output: Outputs, session: Session, upload_dir, collection_name, collections):

    @render.ui
    def collection_view():
        return ui.card(
            ui.markdown(collection_name),
            ui.input_action_button(id="delete", label="Delete")
        )
    
    @reactive.effect
    @reactive.event(input.delete, ignore_init=True)
    def on_delete():
        utility.drop_collection(collection_name)
        collections.set(get_collections())

@module.ui
def collection_management_ui():
    return [
        ui.markdown("# Collection Management"),
        ui.output_ui("collection_management_content")
    ]

@module.server
def collection_management_server(input: Inputs, output: Outputs, session: Session, upload_dir, selected_collection, collections, milvus_status):

    collection_create_server("collection_create", selected_collection, collections)

    @render.ui
    def collection_management_content():
        if milvus_status.get():
            return ui.TagList(
                collection_create_ui("collection_create"),
                ui.output_ui("collection_list") 
            )
        else:
            return ui.markdown("Milvus is offline!")

    @render.ui
    def collection_list():
        return [collection_item_ui(f"collection_item_{collection}") for collection in collections.get()]
    
    @reactive.effect
    def collection_item_servers():
        for collection in collections.get():
            collection_item_server(f"collection_item_{collection}", upload_dir, collection, collections)