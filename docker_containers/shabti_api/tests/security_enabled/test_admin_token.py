from shabti_keycloak import get_keycloak_admin_openid_token
from ...src.app.document_collections import get_collections
import pytest


@pytest.mark.parametrize(
    "shabti_collection_id",
    [
        {"username": "testadmin", "location": "private"},
    ],
    indirect=True,
)
async def test_list_collections(shabti_collection_id):
    token = get_keycloak_admin_openid_token()
    collections = await get_collections(token["access_token"])
    assert next(
        (
            collection
            for collection in collections
            if collection.collection_id == shabti_collection_id
        ),
        None,
    )
