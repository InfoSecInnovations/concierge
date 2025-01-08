from concierge_backend_lib.authentication import (
    get_keycloak_client,
    get_keycloak_admin_openid_token,
)
from concierge_backend_lib.document_collections import (
    create_collection,
    delete_collection,
)
from concierge_backend_lib.ingesting import insert_document
from concierge_backend_lib.loading import load_file
import os

keycloak_client = get_keycloak_client()
# track all created collection IDs here (some of the lookup may get overwritten)
collection_ids = []


async def create_collection_for_user(user, location, collection_name):
    token = keycloak_client.token(user, "test")
    collection_id = await create_collection(
        token["access_token"], collection_name, location
    )
    collection_ids.append(collection_id)
    return collection_id


# we will use the same file for each test
doc = load_file(os.path.join(os.path.dirname(__file__), "..", "assets", "test_doc.txt"))


async def ingest_document(user, collection_id):
    token = keycloak_client.token(user, "test")
    async for _, _, doc_id in insert_document(
        token["access_token"], collection_id, doc
    ):
        pass
    return doc_id


async def clean_up_collections():
    token = get_keycloak_admin_openid_token()
    for id in collection_ids:
        token = get_keycloak_admin_openid_token()
        # the tests may have deleted some of these, so we allow exceptions here
        try:
            await delete_collection(token["access_token"], id)
        except Exception:
            pass
