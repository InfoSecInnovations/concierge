# This test should be run once Concierge is installed with the demo RBAC configuration
# For best results it should be fresh installation with no collections created or tweaks made to the access controls
# Do not use this on a production instance!

from concierge_backend_lib.authentication import (
    get_keycloak_client,
    get_keycloak_admin_openid_token,
)
from concierge_backend_lib.authorization import UnauthorizedOperationError
from concierge_backend_lib.document_collections import (
    create_collection,
    delete_collection,
    get_documents,
)
from concierge_backend_lib.ingesting import insert_document
from concierge_backend_lib.loading import load_file
import pytest
from keycloak import KeycloakPostError
import asyncio
import os

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


@pytest.mark.parametrize(
    "user,collection_name",
    [
        ("testadmin", "testadmin's shared collection"),
        ("testadmin", "testadmin's private collection"),
        ("testadmin", "testprivate's private collection"),
        ("testsharedread", "testadmin's shared collection"),
        ("testshared", "testadmin's shared collection"),
        ("testprivate", "testprivate's private collection"),
    ],
)
async def test_can_read_collection(user, collection_name):
    token = keycloak_client.token(user, "test")
    docs = await get_documents(
        token["access_token"], collection_lookup[collection_name]
    )
    assert docs is not None


@pytest.mark.parametrize(
    "user,collection_name",
    [
        ("testsharedread", "testadmin's private collection"),
        ("testshared", "testadmin's private collection"),
        ("testprivate", "testadmin's private collection"),
        ("testprivate", "testadmin's shared collection"),
        ("testnothing", "testadmin's shared collection"),
        ("testnothing", "testadmin's private collection"),
    ],
)
async def test_cannot_read_collection(user, collection_name):
    with pytest.raises((UnauthorizedOperationError, KeycloakPostError)):
        token = keycloak_client.token(user, "test")
        await get_documents(token["access_token"], collection_lookup[collection_name])


# we will use the documents created in the next tests
document_lookup = {}
# we will use the same file for each test
doc = load_file(os.path.join(os.path.dirname(__file__), "test_doc.txt"))


async def ingest_document(user, collection_name):
    token = keycloak_client.token(user, "test")
    async for _, _, doc_id in insert_document(
        token["access_token"], collection_lookup[collection_name], doc
    ):
        pass
    document_lookup[f"{collection_name} document"] = doc_id
    return doc_id


@pytest.mark.parametrize(
    "user,collection_name",
    [
        ("testadmin", "testadmin's shared collection"),
        ("testadmin", "testadmin's private collection"),
        ("testadmin", "testprivate's private collection"),
        ("testshared", "testadmin's shared collection"),
        ("testprivate", "testprivate's private collection"),
    ],
)
async def test_can_ingest_document(user, collection_name):
    assert await ingest_document(user, collection_name)


@pytest.mark.parametrize(
    "user,collection_name",
    [
        ("testsharedread", "testadmin's private collection"),
        ("testsharedread", "testadmin's shared collection"),
        ("testshared", "testadmin's private collection"),
        ("testprivate", "testadmin's private collection"),
        ("testprivate", "testadmin's shared collection"),
        ("testnothing", "testadmin's shared collection"),
        ("testnothing", "testadmin's private collection"),
    ],
)
async def test_cannot_ingest_document(user, collection_name):
    with pytest.raises((UnauthorizedOperationError, KeycloakPostError)):
        await ingest_document(user, collection_name)


async def teardown():
    token = get_keycloak_admin_openid_token()
    for id in collection_lookup.values():
        token = get_keycloak_admin_openid_token()
        await delete_collection(token["access_token"], id)


def teardown_module():
    asyncio.run(teardown())
