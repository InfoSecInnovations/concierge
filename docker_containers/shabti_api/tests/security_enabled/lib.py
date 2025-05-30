from app.authentication import (
    get_keycloak_client,
    get_keycloak_admin_openid_token,
)
from app.document_collections import (
    create_collection,
    delete_collection,
)
from app.ingesting import insert_document
from app.loading import load_file
import os


# track all created collection IDs here (some of the lookup may get overwritten)
collection_ids = []


async def create_collection_for_user(user, location, collection_name):
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    collection_info = await create_collection(
        token["access_token"], collection_name, location
    )
    collection_ids.append(collection_info.collection_id)
    return collection_info.collection_id


filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)
# we will use the same file for each test
doc = load_file(file_path, filename)
with open(file_path, "rb") as f:
    binary = f.read()


async def ingest_document(user, collection_id):
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    async for ingest_info in insert_document(
        token["access_token"], collection_id, doc, binary
    ):
        pass
    return ingest_info.document_id


async def clean_up_collections():
    token = get_keycloak_admin_openid_token()
    for id in collection_ids:
        token = get_keycloak_admin_openid_token()
        # the tests may have deleted some of these, so we allow exceptions here
        try:
            await delete_collection(token["access_token"], id)
        except Exception:
            pass
