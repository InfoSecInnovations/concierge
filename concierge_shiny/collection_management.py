from shiny import module, reactive, ui, render, Inputs, Outputs, Session
from components import (
    collection_create_ui,
    collection_create_server,
    collection_selector_ui,
    collection_selector_server,
)
from util.async_single import asyncify
from concierge_backend_lib.opensearch import (
    get_indices,
    delete_index,
    get_documents,
    delete_document,
)
from ingester import ingester_ui, ingester_server
from shiny._utils import rand_hex

# --------
# DOCUMENT
# --------


@module.ui
def document_ui(doc):
    return ui.card(
        ui.markdown(f"""
{doc['type']}: {doc['source']}

{doc['vector_count']} vectors
"""),
        ui.input_task_button("delete_doc", "Delete"),
    )


@module.server
def document_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    client,
    collection,
    doc,
    deletion_callback,
):
    deleting = reactive.value(False)

    @ui.bind_task_button(button_id="delete_doc")
    @reactive.extended_task
    async def delete():
        await asyncify(delete_document, client, collection, doc["type"], doc["source"])
        deleting.set(False)

    @reactive.effect
    @reactive.event(input.delete_doc, ignore_init=True)
    def on_delete():
        deleting.set(True)
        delete()

    @reactive.effect
    @reactive.event(deleting, ignore_none=False, ignore_init=True)
    def on_delete_done():
        if not deleting.get():
            deletion_callback()


# --------
# MAIN
# --------


@module.ui
def collection_management_ui():
    return [
        ui.markdown("# Collection Management"),
        ui.output_ui("collection_management_content"),
    ]


@module.server
def collection_management_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    upload_dir,
    selected_collection,
    collections,
    opensearch_status,
    client,
):
    collection_create_server(
        "collection_create", selected_collection, collections, client
    )
    collection_selector_server("collection_select", selected_collection, collections)
    ingestion_done_trigger = ingester_server(
        "ingester", upload_dir, selected_collection, collections, client
    )

    document_delete_trigger = reactive.value(0)
    current_docs = reactive.value([])
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
            return ui.TagList(
                ui.accordion(
                    ingester_ui("ingester"),
                    ui.accordion_panel(
                        ui.markdown("#### Manage Documents"),
                        ui.output_ui("collection_documents"),
                    ),
                    id="collection_management_accordion",
                    class_="mb-3",
                ),
                ui.input_task_button(id="delete", label="Delete Collection"),
            )
        return ui.markdown("Please create a collection first!")

    @render.ui
    def collection_documents():
        if fetching_docs.get():
            return ui.markdown("#### Fetching documents in collection...")
        return ui.TagList(
            ui.markdown(f"#### {len(current_docs.get())} documents in collection"),
            *[document_ui(doc["id"], doc) for doc in current_docs.get()],
        )

    @ui.bind_task_button(button_id="delete")
    @reactive.extended_task
    async def delete(collection_name):
        await asyncify(delete_index, client, collection_name)
        new_collections = await asyncify(get_indices, client)
        collections.set(new_collections)
        if not new_collections:
            selected_collection.set(None)
        else:
            selected_collection.set(new_collections[0])

    @reactive.effect
    @reactive.event(input.delete, ignore_init=True)
    def on_delete():
        delete(selected_collection.get())

    @reactive.extended_task
    async def get_documents_task(collection_name):
        docs = await asyncify(get_documents, client, collection_name)
        fetching_docs.set(False)
        current_docs.set([{**doc, "id": rand_hex(4)} for doc in docs])

    @reactive.effect
    @reactive.event(
        selected_collection,
        ingestion_done_trigger,
        document_delete_trigger,
        ignore_none=False,
    )
    def on_collection_change():
        fetching_docs.set(True)
        get_documents_task(selected_collection.get())

    @reactive.effect
    def document_servers():
        for doc in current_docs.get():
            document_server(
                doc["id"], client, selected_collection.get(), doc, on_delete_document
            )
