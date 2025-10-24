import os
import pytest
from .lib import get_client_for_user, get_admin_client
import asyncio
from shabti_api_client import ShabtiAuthenticationError

collection_lookup = {}

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


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
    client = await get_client_for_user(user)
    collection_name = f"{user}'s {location} collection"
    collection_id = await client.create_collection(collection_name, location)
    assert collection_id
    collection_lookup[collection_name] = collection_id


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
    with pytest.raises(ShabtiAuthenticationError):
        client = await get_client_for_user(user)
        collection_name = f"{user}'s {location} collection"
        await client.create_collection(collection_name, location)


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
    client = await get_client_for_user(user)
    docs = await client.get_documents(collection_lookup[collection_name])
    assert isinstance(docs, list)


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
    with pytest.raises(ShabtiAuthenticationError):
        client = await get_client_for_user(user)
        await client.get_documents(collection_lookup[collection_name])


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
    client = await get_client_for_user(user)
    document_id = None
    async for info in client.insert_files(
        collection_lookup[collection_name], [file_path]
    ):
        document_id = info.document_id
    assert document_id


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
    with pytest.raises(ShabtiAuthenticationError):
        client = await get_client_for_user(user)
        async for info in client.insert_files(
            collection_lookup[collection_name], [file_path]
        ):
            pass


async def clean_up_collections():
    client = await get_admin_client()
    collections = await client.get_collections()
    for collection in collections:
        await client.delete_collection(collection.collection_id)


def teardown_module():
    asyncio.run(clean_up_collections())
