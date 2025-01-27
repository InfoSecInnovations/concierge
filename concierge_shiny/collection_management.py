from shiny import module, reactive, ui, render, Inputs, Outputs, Session, req
from components import (
    collection_create_ui,
    collection_create_server,
    collection_selector_ui,
    collection_selector_server,
)
from isi_util.list_util import find
from concierge_backend_lib.document_collections import (
    get_collection_scopes,
    delete_collection,
    get_documents,
    delete_document,
    get_collections,
)
from concierge_backend_lib.authorization import auth_enabled
from ingester import ingester_ui, ingester_server
from shiny._utils import rand_hex
from functions import doc_link, format_collection_name
from markdown_renderer import md
from collections_data import CollectionsData
from auth import WebAppAsyncTokenTaskRunner

# --------
# DOCUMENT
# --------


@module.ui
def document_ui(collection_name, doc, can_delete):
    card_elements = [
        ui.markdown(
            f"""
{doc_link(collection_name, doc)}

{doc["vector_count"]} vectors
""",
            render_func=md.render,
        )
    ]
    if can_delete:
        card_elements.append(ui.input_task_button("delete_doc", "Delete"))
    return ui.card(*card_elements)


@module.server
def document_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    task_runner: WebAppAsyncTokenTaskRunner,
    collection,
    doc,
    deletion_callback,
):
    deleting = reactive.value(False)

    @ui.bind_task_button(button_id="delete_doc")
    @reactive.extended_task
    async def delete():
        async def do_delete(token):
            await delete_document(
                token["access_token"],
                collection,
                doc["type"],
                doc["id"],
            )

        return await task_runner.run_async_task(do_delete)

    @reactive.effect()
    def delete_effect():
        delete.result()
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
    selected_collection,
    collections,
    opensearch_status,
    task_runner: WebAppAsyncTokenTaskRunner,
    user_info,
    permissions,
):
    collection_create_server(
        "collection_create", selected_collection, collections, task_runner, permissions
    )
    collection_selector_server(
        "collection_select", selected_collection, collections, user_info
    )
    ingestion_done_trigger = ingester_server(
        "ingester", selected_collection, collections, task_runner, user_info
    )

    document_delete_trigger = reactive.value(0)
    current_docs = reactive.value([])
    current_scopes = reactive.value({})
    fetching_docs = reactive.value(False)
    auth_is_enabled = auth_enabled()

    def on_delete_document():
        document_delete_trigger.set(document_delete_trigger.get() + 1)

    @render.ui
    def collection_management_content():
        if opensearch_status.get():

            def show_toggle():
                if not auth_is_enabled:
                    return False
                return len(permissions.get()) > 1

            return ui.TagList(
                collection_create_ui("collection_create", show_toggle()),
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
            elif not auth_is_enabled or "update" in current_scopes.get():
                accordion_elements.append(ingester_ui("ingester"))
            else:
                accordion_elements.append(
                    ui.accordion_panel(
                        ui.markdown(
                            "#### You don't have permission to ingest documents into this collection"
                        ),
                        value="ingest_documents",
                    )
                )
            accordion_elements.append(
                ui.accordion_panel(
                    ui.output_ui("documents_title"),
                    ui.output_ui("collection_documents"),
                    value="manage_documents",
                )
            )
            items = [
                ui.markdown(
                    f"### Selected collection: {format_collection_name(find(collections.get().collections, lambda collection: collection['_id'] == selected_collection.get()), user_info.get())}"
                ),
                ui.accordion(
                    *accordion_elements,
                    id="collection_management_accordion",
                    class_="mb-3",
                ),
            ]
            if not auth_is_enabled or "delete" in current_scopes.get():
                items.append(
                    ui.input_task_button(id="delete", label="Delete Collection")
                )
            print("sup")
            return ui.TagList(*items)
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
                document_ui(
                    doc["el_id"],
                    selected_collection.get(),
                    doc,
                    not auth_is_enabled or "update" in current_scopes.get(),
                )
                for doc in current_docs.get()
            ],
        )

    @ui.bind_task_button(button_id="delete")
    @reactive.extended_task
    async def delete(collection_id):
        async def do_delete(token):
            await delete_collection(token["access_token"], collection_id)
            return await get_collections(token["access_token"])

        return await task_runner.run_async_task(do_delete)

    @reactive.effect
    def delete_effect():
        new_collections = delete.result()
        collections.set(
            CollectionsData(
                collections=new_collections,
                loading=False,
            )
        )
        if len(new_collections):
            selected_collection.set(new_collections[0]["_id"])
        else:
            selected_collection.set(None)

    @reactive.effect
    @reactive.event(input.delete, ignore_init=True)
    def on_delete():
        delete(selected_collection.get())

    @reactive.extended_task
    async def get_documents_task(collection_id):
        async def do_get_documents(token):
            scopes = await get_collection_scopes(token["access_token"], collection_id)
            docs = await get_documents(token["access_token"], collection_id)
            return (scopes, docs)

        return await task_runner.run_async_task(do_get_documents)

    @reactive.effect
    def get_documents_effect():
        scopes, docs = get_documents_task.result()
        current_scopes.set(scopes)
        fetching_docs.set(False)
        current_docs.set([{**doc, "el_id": rand_hex(4)} for doc in docs])

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
                doc["el_id"],
                task_runner,
                selected_collection.get(),
                doc,
                on_delete_document,
            )
