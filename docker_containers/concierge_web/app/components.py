from shiny import module, reactive, ui, req, render, Inputs, Outputs, Session
from shiny._utils import rand_hex
from isi_util.async_single import asyncify
import os
from .functions import format_collection_name
from concierge_util import auth_enabled
from .common.collections_data import CollectionsData

# --------
# COLLECTION SELECTOR
# --------


@module.server
def collection_selector_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    selected_collection,
    collections,
    user_info,
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
                collection["_id"]: format_collection_name(collection, user_info.get())
                for collection in collections.get().collections
            },
            selected=selected_collection.get(),
        )

    @reactive.effect
    def update_selection():
        selected_collection.set(input.internal_selected_collection())


# --------
# COLLECTION CREATOR
# --------

COLLECTION_PLACEHOLDER = "new_collection_name"


@module.ui
def collection_create_ui(show_toggle):
    elements = [
        text_input_enter_ui("new_collection", "New Collection", COLLECTION_PLACEHOLDER)
    ]
    if show_toggle:
        elements.append(ui.input_checkbox("toggle_shared", "Shared Collection"))
    return elements


@module.server
def collection_create_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    selected_collection,
    collections,
    task_runner: WebAppAsyncTokenTaskRunner,
    permissions,
):
    creating = reactive.value(False)
    new_collection_name = text_input_enter_server("new_collection", creating)

    @reactive.extended_task
    async def create_concierge_collection(collection_name, location):
        async def do_create(token):
            collection_id = await create_collection(
                token["access_token"],
                collection_name,
                location,
            )
            new_collections = await get_collections(token["access_token"])
            return (collection_id, new_collections)

        return await task_runner.run_async_task(do_create)

    @reactive.effect
    def create_collection_effect():
        try:
            collection_id, new_collections = create_concierge_collection.result()
            collections.set(
                CollectionsData(
                    collections=new_collections,
                    loading=False,
                )
            )
            selected_collection.set(collection_id)
        except CollectionExistsError:
            ui.notification_show(
                "Collection with this name already exists", type="error"
            )
        creating.set(False)

    @reactive.effect
    @reactive.event(new_collection_name, ignore_none=True, ignore_init=True)
    def on_create():
        req(new_collection_name())
        new_name = new_collection_name()
        if not new_name:
            return
        if not auth_enabled():
            location = None
        else:
            perms = permissions.get()
            if "collection:private:create" not in perms:
                location = "shared"
            elif "collection:shared:create" not in perms:
                location = "private"
            else:
                location = "shared" if input.toggle_shared() else "private"
        creating.set(True)
        create_concierge_collection(new_name, location)
