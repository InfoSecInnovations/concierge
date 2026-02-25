from shiny import module, reactive, render, ui, Inputs, Outputs, Session
from .collection_document import document_ui, document_server
from .document_item import DocumentItem
from shabti_api_client import BaseShabtiClient
from shiny._utils import rand_hex
import math

RESULTS_PER_PAGE = 10
PAGES_IN_LIST = 10


@module.ui
def page_link_ui(label, is_current=False):
    return ui.input_action_link(
        "select_page",
        label,
        class_=f"px-1 {'link-underline link-underline-opacity-0' if is_current else ''}",
    )


@module.server
def page_link_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    page_number: int,
    current_page: reactive.Value[int],
):
    @reactive.effect
    @reactive.event(input.select_page, ignore_init=True)
    def on_click():
        current_page.set(page_number)


@module.ui
def page_list_ui():
    return ui.output_ui("page_list_view")


@module.server
def page_list_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    current_page: reactive.Value[int],
    total_result_count: reactive.Value[int],
):
    first_page = reactive.value(0)
    total_pages = reactive.value(0)

    @reactive.effect
    def set_page_counts():
        current_index = current_page.get()
        total_page_count = math.ceil(total_result_count.get() / RESULTS_PER_PAGE)
        first_page_index = current_index - PAGES_IN_LIST / 2
        if first_page_index < 0:
            first_page_index = 0
        first_page_index = max(
            0, min(total_page_count - PAGES_IN_LIST, first_page_index)
        )
        first_page.set(first_page_index)
        total_pages.set(total_page_count)
        page_link_server("select_page_first", 0, current_page)
        for i in range(min(total_page_count, PAGES_IN_LIST)):
            page_link_server(
                f"select_page_{first_page_index + i}",
                first_page_index + i,
                current_page,
            )
        page_link_server("select_page_last", total_page_count - 1, current_page)

    @render.ui
    def page_list_view():
        total_page_count = total_pages.get()
        if not total_page_count:
            return []
        first_page_index = first_page.get()
        current_index = current_page.get()
        return [
            page_link_ui("select_page_first", "First", current_index == 0),
            *[
                page_link_ui(
                    f"select_page_{first_page_index + i}",
                    first_page_index + i + 1,
                    first_page_index + i == current_index,
                )
                for i in range(min(total_page_count, PAGES_IN_LIST))
            ],
            page_link_ui("select_page_last", "Last", current_index == total_page_count),
        ]


@module.ui
def document_list_ui():
    return [
        ui.output_ui("search_view"),
        ui.output_ui("document_list_view"),
        page_list_ui("bottom_page_nav"),
    ]


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
    current_page: reactive.Value[int] = reactive.value(0)
    document_types: reactive.Value[list[str]] = reactive.value([])
    print("document list server")
    print(selected_collection)

    @reactive.extended_task
    async def get_document_types_task(collection_id: str):
        return await client.get_document_types(collection_id)

    @reactive.effect
    def get_document_types_effect():
        doc_types = get_document_types_task.result()
        document_types.set(doc_types)

    @reactive.extended_task
    async def get_documents_task(
        collection_id: str,
        page: int,
        search: str,
        sort: str,
        filter_document_type: list[str],
    ):
        print("get_documents_task")
        print(collection_id)
        return await client.get_documents(
            collection_id,
            max_results=RESULTS_PER_PAGE,
            page=page,
            search=search,
            sort=sort,
            filter_document_type=filter_document_type,
        )

    def on_delete_document():
        get_documents_task(
            selected_collection,
            current_page.get(),
            input.search(),
            input.sort(),
            input.filter_document_type(),
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
            ui.input_text("search", "Search", width="100%"),
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
            page_list_ui("top_page_nav"),
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

    page_list_server("top_page_nav", current_page, total_results_count)
    page_list_server("bottom_page_nav", current_page, total_results_count)

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

    @reactive.effect
    def get_documents():
        get_documents_task(
            selected_collection,
            page=current_page.get(),
            search=input.search(),
            sort=input.sort(),
            filter_document_type=input.filter_document_type(),
        )

    @reactive.effect
    def get_document_types():
        get_document_types_task(selected_collection)

    @reactive.effect
    @reactive.event(
        input.search,
        input.sort,
        input.filter_document_type,
        ignore_init=True,
        ignore_none=False,
    )
    def reset_current_page():
        current_page.set(0)

    @reactive.effect
    @reactive.event(
        total_results_count,
        ignore_init=True,
        ignore_none=False,
    )
    def reset_current_page_if_out_of_range():
        total_pages = math.ceil(total_results_count.get() / RESULTS_PER_PAGE)
        if total_pages and current_page.get() >= total_pages:
            current_page.set(total_pages - 1)
