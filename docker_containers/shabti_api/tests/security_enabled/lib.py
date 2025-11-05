from shabti_keycloak import (
    get_keycloak_client,
)
from ...src.app.document_collections import (
    create_collection,
)


async def create_collection_for_user(user, location, collection_name):
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    collection_info = await create_collection(
        token["access_token"], collection_name, location
    )
    return collection_info.collection_id
