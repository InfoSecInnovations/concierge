import os
import pytest
from .lib import get_client_for_user, get_admin_client
import asyncio
from shabti_api_client import ShabtiAuthenticationError
import secrets

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


async def ingest_document(user, collection_name):
    client = await get_client_for_user(user)
    document_id = None
    async for info in client.insert_files(
        collection_lookup[collection_name], [file_path]
    ):
        document_id = info.document_id
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
    with pytest.raises(ShabtiAuthenticationError):
        await ingest_document(user, collection_name)


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
async def can_delete_document(user, collection_name):
    document_id = await ingest_document(
        "testadmin", collection_name
    )  # ingest document as admin as we're only testing deletion here
    client = await get_client_for_user(user)
    await client.delete_document(collection_lookup[collection_name], document_id)
    documents = await client.get_documents(collection_lookup[collection_name])
    assert not any(doc.document_id == document_id for doc in documents)


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
    document_id = await ingest_document(
        "testadmin", collection_name
    )  # ingest document as admin as we're only testing deletion here
    with pytest.raises(ShabtiAuthenticationError):
        client = await get_client_for_user(user)
        await client.delete_document(collection_lookup[collection_name], document_id)


async def create_collection_for_deletion(owner, location):
    client = await get_admin_client()
    return await client.create_collection(secrets.token_hex(8), location, owner)


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
    collection_id = await create_collection_for_deletion(owner, location)
    client = await get_client_for_user(user)
    await client.delete_collection(collection_id)
    collections = await client.get_collections()
    assert not any(
        collection.collection_id == collection_id for collection in collections
    )


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
    collection_id = await create_collection_for_deletion(owner, location)
    with pytest.raises(ShabtiAuthenticationError):
        client = await get_client_for_user(user)
        await client.delete_collection(collection_id)


async def clean_up_collections():
    client = await get_admin_client()
    collections = await client.get_collections()
    for collection in collections:
        await client.delete_collection(collection.collection_id)


def teardown_module():
    asyncio.run(clean_up_collections())
