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
    total_results_count: reactive.Value[int] = reactive.value(0)
    total_documents_count: reactive.Value[int] = reactive.value(0)
    document_delete_trigger = reactive.value(0)
    current_page: reactive.Value[int] = reactive.value(0)
    filter_document_type: reactive.Value[str] = reactive.value("")
    document_types: reactive.Value[list[str]] = reactive.value([])

    def on_delete_document():
        document_delete_trigger.set(document_delete_trigger.get() + 1)

    @reactive.extended_task
    async def get_document_types_task(collection_id: str):
        return await client.get_document_types(collection_id)

    @reactive.effect
    def get_document_types_effect():
        doc_types = get_document_types_task.result()
        document_types.set(doc_types)

    @reactive.extended_task
    async def get_documents_task(
        collection_id: str, page: int, search: str, sort: str, filter_document_type: str
    ):
        return await client.get_documents(
            collection_id,
            max_results=RESULTS_PER_PAGE,
            page=page,
            search=search,
            sort=sort,
            filter_document_type=filter_document_type,
        )

    @reactive.effect
    def get_documents_effect():
        docs = get_documents_task.result()
        current_docs.set(
            [
                DocumentItem(**doc.model_dump(), element_id=rand_hex(4))
                for doc in docs.documents
            ]
        )
        total_results_count.set(docs.total_hits)
        total_documents_count.set(docs.total_documents)

    @render.ui
    def document_list_view():
        return [
            document_ui(doc.element_id, selected_collection, doc, can_delete)
            for doc in current_docs.get()
        ]

    @render.ui
    def search_view():
        return [
            ui.output_ui("query_info"),
            ui.input_text("search", "Search"),
            ui.layout_columns(
                ui.input_select(
                    "sort",
                    "Sort By",
                    {
                        "relevance": "Relevance",
                        "date_desc": "Newest",
                        "date_asc": "Oldest",
                    },
                ),
                ui.input_selectize(
                    "filter_document_type",
                    "Filter By Document Type",
                    document_types.get(),
                    multiple=True,
                ),
            ),
        ]

    @render.ui
    def query_info():
        elements = [
            ui.markdown(f"{total_documents_count.get()} Documents in collection")
        ]
        if ("search" in input and input.search()) or (
            "filter_document_type" in input and input.filter_document_type()
        ):
            elements.append(
                ui.markdown(
                    f"{total_results_count.get()} Documents match the current query"
                )
            )
        return elements

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
    def get_documents():
        req(selected_collection)
        get_documents_task(
            selected_collection,
            page=current_page.get(),
            search=input.search(),
            sort=input.sort(),
            filter_document_type=filter_document_type.get(),
        )

    @reactive.effect()
    def get_document_types():
        req(selected_collection)
        get_document_types_task(selected_collection)
