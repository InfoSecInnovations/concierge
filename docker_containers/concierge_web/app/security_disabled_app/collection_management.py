from shiny import module, reactive, ui, render, Inputs, Outputs, Session, req
from ..common.ingester import ingester_ui, ingester_server
from shiny._utils import rand_hex
from .collections_data import CollectionsData
from concierge_api_client import ConciergeClient
from .collection_create import collection_create_ui, collection_create_server
from ..common.collection_selector_ui import collection_selector_ui
from .collection_selector_server import collection_selector_server
from ..common.collection_document import document_ui, document_server
from ..common.document_item import DocumentItem


@module.server
def collection_management_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    client: ConciergeClient,
    selected_collection: reactive.Value,
    collections: reactive.Value[CollectionsData],
    opensearch_status: reactive.Value,
):
    collection_create_server(
        "collection_create", client, selected_collection, collections
    )
    collection_selector_server("collection_select", selected_collection, collections)
    ingestion_done_trigger = ingester_server(
        "ingester", selected_collection, client.insert_files, client.insert_urls
    )

    document_delete_trigger = reactive.value(0)
    current_docs: reactive.Value[list[DocumentItem]] = reactive.value([])
    fetching_docs = reactive.value(False)

    def on_delete_document():
        document_delete_trigger.set(document_delete_trigger.get() + 1)

    @render.ui
    def collection_management_content():
        if opensearch_status.get():
            return ui.TagList(
                collection_create_ui("collection_create"),
                collection_selector_ui("collection_select"),
                ui.output_ui("collection_view"),
            )
        else:
            return ui.markdown("OpenSearch is offline!")

    @render.ui
    def collection_view():
        if selected_collection.get():
            accordion_elements = []
            fetching = fetching_docs.get()
            if fetching:
                accordion_elements.append(
                    ui.accordion_panel(
                        ui.markdown("#### Loading collection..."),
                        value="ingest_documents",
                    )
                )
            else:
                accordion_elements.append(ingester_ui("ingester"))
            accordion_elements.append(
                ui.accordion_panel(
                    ui.output_ui("documents_title"),
                    ui.output_ui("collection_documents"),
                    value="manage_documents",
                )
            )
            return ui.TagList(
                [
                    ui.markdown(
                        f"### Selected collection: {collections.get().collections[selected_collection.get()].collection_name}"
                    ),
                    ui.accordion(
                        *accordion_elements,
                        id="collection_management_accordion",
                        class_="mb-3",
                    ),
                    ui.input_task_button(id="delete", label="Delete Collection"),
                ]
            )
        if collections.get().loading:
            return ui.markdown("Loading collections...")
        return ui.markdown("Please create a collection first!")

    @render.ui
    def documents_title():
        if fetching_docs.get():
            return ui.markdown("#### Loading collection...")
        return ui.div(
            ui.markdown("#### Manage Documents"),
            ui.markdown(f"({len(current_docs.get())} documents in collection)"),
        )

    @render.ui
    def collection_documents():
        if fetching_docs.get():
            return ui.markdown("#### Loading collection...")
        return ui.TagList(
            *[
                document_ui(doc.element_id, selected_collection.get(), doc, True)
                for doc in current_docs.get()
            ],
        )

    @ui.bind_task_button(button_id="delete")
    @reactive.extended_task
    async def delete(collection_id):
        await client.delete_collection(collection_id)
        return await client.get_collections()

    @reactive.effect
    def delete_effect():
        new_collections = delete.result()
        collections.set(
            CollectionsData(
                collections={
                    collection.collection_id: collection
                    for collection in new_collections
                },
                loading=False,
            )
        )
        if len(new_collections):
            selected_collection.set(new_collections[0].collection_id)
        else:
            selected_collection.set(None)

    @reactive.effect
    @reactive.event(input.delete, ignore_init=True)
    def on_delete():
        delete(selected_collection.get())

    @reactive.extended_task
    async def get_documents_task(collection_id: str):
        return await client.get_documents(collection_id)

    @reactive.effect
    def get_documents_effect():
        docs = get_documents_task.result()
        fetching_docs.set(False)
        current_docs.set(
            [DocumentItem(**doc.model_dump(), element_id=rand_hex(4)) for doc in docs]
        )

    @reactive.effect
    @reactive.event(
        selected_collection,
        ingestion_done_trigger,
        document_delete_trigger,
        ignore_none=False,
    )
    def on_collection_change():
        req(selected_collection.get())
        fetching_docs.set(True)
        get_documents_task(selected_collection.get())

    @reactive.effect
    def document_servers():
        for doc in current_docs.get():
            document_server(
                doc.element_id,
                client.delete_collection,
                selected_collection.get(),
                doc,
                on_delete_document,
            )
