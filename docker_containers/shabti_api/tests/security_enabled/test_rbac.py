# This test should be run once Shabti is installed with the demo RBAC configuration
# For best results it should be fresh installation with no collections created or tweaks made to the access controls
# Do not use this on a production instance!

from shabti_keycloak import get_keycloak_client, get_keycloak_admin_openid_token
from ...app.authorization import UnauthorizedOperationError
from ...app.document_collections import (
    delete_collection,
    get_documents,
    delete_document,
)
import pytest
from keycloak import KeycloakPostError, KeycloakAuthenticationError
import asyncio
import secrets
from .lib import create_collection_for_user, clean_up_collections, ingest_document
from ...app.app import app
from fastapi.testclient import TestClient
import os
import json


# we will use the collections created in the first tests for the subsequent tests
collection_lookup = {}
collection_ids = []

client = TestClient(app)


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
    # test function behind the API call
    collection_name = f"{user}'s {location} collection"
    collection_id = await create_collection_for_user(user, location, collection_name)
    assert collection_id
    collection_lookup[collection_name] = collection_id

    # test the API call itself
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    collection_name = f"{user}'s {location} API collection"
    response = client.post(
        "/collections",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={"collection_name": collection_name, "location": location},
    )
    assert response.status_code == 201
    response_json = response.json()
    assert response_json["collection_id"]
    collection_ids.append(response_json["collection_id"])
    collection_lookup[collection_name] = response_json["collection_id"]


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
    with pytest.raises((KeycloakPostError, KeycloakAuthenticationError)):
        # test function behind the API call
        await create_collection_for_user(
            user, location, f"{user}'s {location} collection"
        )

        # test the API call itself
        keycloak_client = get_keycloak_client()
        token = keycloak_client.token(user, "test")
        collection_name = f"{user}'s {location} API collection"
        client.post(
            "/collections",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            json={"collection_name": collection_name, "location": location},
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
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    docs = await get_documents(
        token["access_token"], collection_lookup[collection_name]
    )
    assert docs is not None
    response = client.get(
        f"/collections/{collection_lookup[collection_name]}/documents",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


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
    with pytest.raises(
        (UnauthorizedOperationError, KeycloakPostError, KeycloakAuthenticationError)
    ):
        keycloak_client = get_keycloak_client()
        token = keycloak_client.token(user, "test")
        await get_documents(token["access_token"], collection_lookup[collection_name])
        client.get(
            f"/collections/{collection_lookup[collection_name]}/documents",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )


filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


def ingest_document_api(user, collection_id):
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    response = client.post(
        f"/collections/{collection_id}/documents/files",
        files=[("files", open(file_path, "rb"))],
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    for item in response.iter_lines():
        line = json.loads(item)
        if "document_id" in line:
            document_id = line["document_id"]
    return document_id


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
    assert await ingest_document(user, collection_lookup[collection_name])
    assert ingest_document_api(user, collection_lookup[collection_name])


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
    with pytest.raises(
        (UnauthorizedOperationError, KeycloakPostError, KeycloakAuthenticationError)
    ):
        await ingest_document(user, collection_lookup[collection_name])
        assert ingest_document_api(user, collection_lookup[collection_name])


async def delete_document_with_user(user, collection_name):
    # create a new entry each time to avoid accidentally trying to delete the same one multiple times
    doc_id = await ingest_document(
        "testadmin", collection_lookup[collection_name]
    )  # testadmin should be able to ingest documents into any collection
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    return await delete_document(
        token["access_token"], collection_lookup[collection_name], "plaintext", doc_id
    )


async def delete_document_api_with_user(user, collection_name):
    # create a new entry each time to avoid accidentally trying to delete the same one multiple times
    doc_id = await ingest_document(
        "testadmin", collection_lookup[collection_name]
    )  # testadmin should be able to ingest documents into any collection
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    return client.delete(
        f"/collections/{collection_lookup[collection_name]}/documents/plaintext/{doc_id}",
        headers={"Authorization": f"Bearer {token['access_token']}"},
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
    response = await delete_document_api_with_user(user, collection_name)
    assert response.status_code == 200
    assert "document_id" in response.json()


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
    with pytest.raises(
        (UnauthorizedOperationError, KeycloakPostError, KeycloakAuthenticationError)
    ):
        await delete_document_with_user(user, collection_name)
        await delete_document_api_with_user(user, collection_name)


async def delete_collection_with_user(user, owner, location):
    # we will create a collection each time to avoid trying to delete an already deleted one
    collection_id = await create_collection_for_user(
        owner, location, secrets.token_hex(8)
    )  # we add a unique identifier to avoid running into name collision issues
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    return await delete_collection(token["access_token"], collection_id)


async def delete_collection_api_with_user(user, owner, location):
    # we will create a collection each time to avoid trying to delete an already deleted one
    collection_id = await create_collection_for_user(
        owner, location, secrets.token_hex(8)
    )  # we add a unique identifier to avoid running into name collision issues
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token(user, "test")
    return client.delete(
        f"/collections/{collection_id}",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )


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
    response = await delete_collection_api_with_user(user, owner, location)
    assert response.status_code == 200
    assert "collection_id" in response.json()


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
    with pytest.raises(
        (UnauthorizedOperationError, KeycloakPostError, KeycloakAuthenticationError)
    ):
        await delete_collection_with_user(user, owner, location)
        await delete_collection_api_with_user(user, owner, location)


async def clean_up_local_collections():
    token = get_keycloak_admin_openid_token()
    for id in collection_ids:
        token = get_keycloak_admin_openid_token()
        # the tests may have deleted some of these, so we allow exceptions here
        try:
            await delete_collection(token["access_token"], id)
        except Exception:
            pass


def teardown_module():
    asyncio.run(clean_up_collections())
    asyncio.run(clean_up_local_collections())
