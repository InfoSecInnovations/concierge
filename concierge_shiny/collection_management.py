from shiny import module, reactive, ui, render, Inputs, Outputs, Session
from components import (
    collection_create_ui, 
    collection_create_server, 
    collection_selector_ui, 
    collection_selector_server
)
from concierge_backend_lib.opensearch import get_indices, delete_index, get_documents
from ingester import ingester_ui, ingester_server

@module.ui
def collection_management_ui():
    return [
        ui.markdown("# Collection Management"),
        ui.output_ui("collection_management_content")
    ]

@module.server
def collection_management_server(input: Inputs, output: Outputs, session: Session, upload_dir, selected_collection, collections, opensearch_status, client):

    collection_create_server("collection_create", selected_collection, collections, client)
    collection_selector_server("collection_select", selected_collection, collections)
    ingestion_done_trigger = ingester_server("ingester", upload_dir, selected_collection, collections, client)

    current_docs = reactive.value([])

    @render.ui
    def collection_management_content():
        if opensearch_status.get():
            return ui.TagList(
                collection_create_ui("collection_create"),
                collection_selector_ui("collection_select"),                              
                ui.output_ui("collection_view")            
            )
        else:
            return ui.markdown("OpenSearch is offline!")

    @render.ui
    def collection_view():
        if selected_collection.get():
            return ui.TagList(
                ui.card(
                    ui.card_header(
                        ui.markdown("### Manage")                        
                    ),
                    *[ui.markdown(f"{doc['type']}: {doc['source']}") for doc in current_docs.get()],
                    ui.input_action_button(id="delete", label="Delete Collection")
                ),
                ingester_ui("ingester")
            )
        return ui.markdown("Please create a collection first!")
    
    @reactive.effect
    @reactive.event(input.delete, ignore_init=True)
    def on_delete():
        delete_index(client, selected_collection.get())      
        new_collections = get_indices(client)
        collections.set(new_collections)
        if not new_collections:
            selected_collection.set(None)
        else:
            selected_collection.set(new_collections[0])

    @reactive.effect
    @reactive.event(selected_collection, ingestion_done_trigger, ignore_none=False)
    def on_collection_change():
        current_docs.set(get_documents(client, selected_collection.get()))