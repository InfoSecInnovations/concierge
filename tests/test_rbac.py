# This test should be run once Concierge is installed with the demo RBAC configuration
# For best results it should be fresh installation with no collections created or tweaks made to the access controls
# Do not use this on a production instance!

from concierge_backend_lib.authentication import (
    get_keycloak_client,
)
from concierge_backend_lib.authorization import UnauthorizedOperationError
from concierge_backend_lib.document_collections import (
    delete_collection,
    get_documents,
    delete_document,
)
from concierge_backend_lib.ingesting import insert_document
from concierge_backend_lib.loading import load_file
import pytest
from keycloak import KeycloakPostError
import asyncio
import os
import secrets
from .lib import create_collection_for_user, clean_up_collections

keycloak_client = get_keycloak_client()

# we will use the collections created in the first tests for the subsequent tests
collection_lookup = {}


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
    assert await create_collection_for_user(
        user, location, collection_lookup, f"{user}'s {location} collection"
    )


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
        await create_collection_for_user(
            user, location, collection_lookup, f"{user}'s {location} collection"
        )


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


# we will use the same file for each test
doc = load_file(os.path.join(os.path.dirname(__file__), "test_doc.txt"))


async def ingest_document(user, collection_name):
    token = keycloak_client.token(user, "test")
    async for _, _, doc_id in insert_document(
        token["access_token"], collection_lookup[collection_name], doc
    ):
        pass
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


async def delete_document_with_user(user, collection_name):
    # create a new entry each time to avoid accidentally trying to delete the same one multiple times
    doc_id = await ingest_document(
        "testadmin", collection_name
    )  # testadmin should be able to ingest documents into any collection
    token = keycloak_client.token(user, "test")
    return await delete_document(
        token["access_token"], collection_lookup[collection_name], "plaintext", doc_id
    )


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
async def test_can_delete_document(user, collection_name):
    assert await delete_document_with_user(user, collection_name)


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
async def test_cannot_delete_document(user, collection_name):
    with pytest.raises((UnauthorizedOperationError, KeycloakPostError)):
        await delete_document_with_user(user, collection_name)


async def delete_collection_with_user(user, owner, location):
    # we will create a collection each time to avoid trying to delete an already deleted one
    collection_id = await create_collection_for_user(
        owner, location, collection_lookup, secrets.token_hex(8)
    )  # we add a unique identifier to avoid running into name collision issues
    token = keycloak_client.token(user, "test")
    await delete_collection(token["access_token"], collection_id)


@pytest.mark.parametrize(
    "user,owner,location",
    [
        ("testadmin", "testadmin", "shared"),
        ("testadmin", "testadmin", "private"),
        ("testadmin", "testshared", "shared"),
        ("testadmin", "testprivate", "private"),
        ("testshared", "testadmin", "shared"),
        ("testprivate", "testprivate", "private"),
    ],
)
async def test_can_delete_collection(user, owner, location):
    await delete_collection_with_user(user, owner, location)


@pytest.mark.parametrize(
    "user,owner,location",
    [
        ("testsharedread", "testadmin", "shared"),
        ("testsharedread", "testadmin", "private"),
        ("testshared", "testadmin", "private"),
        ("testprivate", "testadmin", "private"),
        ("testprivate", "testadmin", "shared"),
        ("testnothing", "testadmin", "shared"),
        ("testnothing", "testadmin", "private"),
    ],
)
async def test_cannot_delete_collection(user, owner, location):
    with pytest.raises((UnauthorizedOperationError, KeycloakPostError)):
        await delete_collection_with_user(user, owner, location)


def teardown_module():
    asyncio.run(clean_up_collections())
