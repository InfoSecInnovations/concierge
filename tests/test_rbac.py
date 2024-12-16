# This test should be run once Concierge is installed with the demo RBAC configuration
# For best results it should be fresh installation with no collections created or tweaks made to the access controls
# Do not use this on a production instance!

from concierge_backend_lib.authentication import (
    get_keycloak_client,
    get_keycloak_admin_openid_token,
)
from concierge_backend_lib.document_collections import (
    create_collection,
    delete_collection,
)
import pytest
from keycloak import KeycloakPostError
import asyncio

keycloak_client = get_keycloak_client()

# we will use the collections created in the first tests for the subsequent tests
collection_lookup = {}


async def create_collection_for_user(user, location):
    token = keycloak_client.token(user, "test")
    collection_name = f"{user}'s {location} collection"
    collection_id = await create_collection(
        token["access_token"], f"{user}'s {location} collection", location
    )
    collection_lookup[collection_name] = collection_id
    return collection_id


@pytest.mark.parametrize(
    "user,location",
    [
        ("testadmin", "private"),
        ("testadmin", "shared"),
        ("testshared", "shared"),
        ("testprivate", "private"),
    ],
)
async def test_can_create_collection(user, location):
    assert await create_collection_for_user(user, location)


@pytest.mark.parametrize(
    "user,location",
    [
        ("testshared", "private"),
        ("testprivate", "shared"),
        ("testsharedread", "private"),
        ("testsharedread", "shared"),
        ("testnothing", "private"),
        ("testnothing", "shared"),
    ],
)
async def test_cannot_create_collection(user, location):
    with pytest.raises(KeycloakPostError):
        await create_collection_for_user(user, location)


async def teardown():
    token = get_keycloak_admin_openid_token()
    for id in collection_lookup.values():
        token = get_keycloak_admin_openid_token()
        await delete_collection(token["access_token"], id)


def teardown_module():
    asyncio.run(teardown())
