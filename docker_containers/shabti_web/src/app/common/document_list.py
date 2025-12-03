from shiny import module, reactive, render, ui, Inputs, Outputs, Session, req
from .collection_document import document_ui, document_server
from .document_item import DocumentItem
from shabti_api_client import BaseShabtiClient
from shiny._utils import rand_hex


RESULTS_PER_PAGE = 10


@module.ui
def document_list_ui():
    return [ui.output_ui("search_view"), ui.output_ui("document_list_view")]


@module.server
def document_list_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    client: BaseShabtiClient,
    selected_collection: str,
    can_delete: bool,
):
    current_docs: reactive.Value[list[DocumentItem]] = reactive.value([])
    total_docs_count: reactive.Value[int] = reactive.value(0)
    document_delete_trigger = reactive.value(0)

    def on_delete_document():
        document_delete_trigger.set(document_delete_trigger.get() + 1)

    @reactive.extended_task
    async def get_documents_task(collection_id: str):
        return await client.get_documents(collection_id)

    @reactive.effect
    def get_documents_effect():
        docs = get_documents_task.result()
        current_docs.set(
            [
                DocumentItem(**doc.model_dump(), element_id=rand_hex(4))
                for doc in docs.documents
            ]
        )
        total_docs_count.set(docs.total_hits)

    @render.ui
    def document_list_view():
        return [
            document_ui(doc.element_id, selected_collection, doc, can_delete)
            for doc in current_docs.get()
        ]

    @render.ui
    def search_view():
        return ui.markdown("TODO")

    @reactive.effect
    def document_servers():
        for doc in current_docs.get():
            document_server(
                doc.element_id,
                client.delete_document,
                selected_collection,
                doc,
                on_delete_document,
            )

    @reactive.effect()
    def on_load():
        req(selected_collection)
        get_documents_task(selected_collection)
