from shiny import module, reactive, ui, req, Inputs, Outputs, Session
from .collections_data import CollectionsData
from concierge_types import CollectionExistsError
from concierge_api_client import ConciergeClient
from ..common.text_input_enter import text_input_enter_ui, text_input_enter_server

COLLECTION_PLACEHOLDER = "new_collection_name"


@module.ui
def collection_create_ui():
    return [text_input_enter_ui("new_collection", "New Collection", COLLECTION_PLACEHOLDER)]


@module.server
def collection_create_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    client: ConciergeClient,
    selected_collection,
    collections,
):
    creating = reactive.value(False)
    new_collection_name = text_input_enter_server("new_collection", creating)

    @reactive.extended_task
    async def create_concierge_collection(collection_name):
        collection_id = await client.create_collection(collection_name)
        new_collections = await client.get_collections()
        return (collection_id, new_collections)

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
        creating.set(True)
        create_concierge_collection(new_name)