from .lib import create_collection_for_user
from shabti_keycloak import get_keycloak_admin_openid_token
from ...src.app.document_collections import get_collections

collection_name = "admin test testadmin's private collection"


async def test_list_collections():
    collection_id = await create_collection_for_user(
        "testadmin", "private", collection_name
    )
    token = get_keycloak_admin_openid_token()
    collections = await get_collections(token["access_token"])
    assert next(
        (
            collection
            for collection in collections
            if collection.collection_id == collection_id
        ),
        None,
    )
