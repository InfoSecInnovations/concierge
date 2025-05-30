from shiny import module, reactive, ui, req, render, Inputs, Outputs, Session
from ..common.collections_data import CollectionsData
from shabti_types import CollectionInfo


@module.server
def collection_selector_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    selected_collection: reactive.Value,
    collections: reactive.Value[CollectionsData[CollectionInfo]],
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
                collection.collection_id: collection.collection_name
                for collection in collections.get().collections.values()
            },
            selected=selected_collection.get(),
        )

    @reactive.effect
    def update_selection():
        selected_collection.set(input.internal_selected_collection())
