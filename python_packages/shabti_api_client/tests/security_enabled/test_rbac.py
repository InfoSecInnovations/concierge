import os
import pytest
from shabti_api_client import ShabtiAuthenticationError
import secrets

collection_lookup = {}

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


@pytest.mark.parametrize(
    "shabti_user_client,location",
    [
        ("testadmin", "private"),
        ("testadmin", "shared"),
        ("testshared", "shared"),
        ("testprivate", "private"),
    ],
    indirect=["shabti_user_client"],
)
async def test_can_create_collection(shabti_user_client, location):
    collection_name = secrets.token_hex(8)
    collection_id = await shabti_user_client.create_collection(
        collection_name, location
    )
    assert collection_id


@pytest.mark.parametrize(
    "shabti_user_client,location",
    [
        ("testshared", "private"),
        ("testprivate", "shared"),
        ("testsharedread", "private"),
        ("testsharedread", "shared"),
        ("testnothing", "private"),
        ("testnothing", "shared"),
    ],
    indirect=["shabti_user_client"],
)
async def test_cannot_create_collection(shabti_user_client, location):
    with pytest.raises(ShabtiAuthenticationError):
        collection_name = secrets.token_hex(8)
        await shabti_user_client.create_collection(collection_name, location)


@pytest.mark.parametrize(
    "shabti_user_client,shabti_collection_id",
    [
        ("testadmin", {"username": "testadmin", "location": "shared"}),
        ("testadmin", {"username": "testadmin", "location": "private"}),
        ("testadmin", {"username": "testprivate", "location": "private"}),
        ("testsharedread", {"username": "testadmin", "location": "shared"}),
        ("testshared", {"username": "testadmin", "location": "shared"}),
        ("testprivate", {"username": "testprivate", "location": "private"}),
    ],
    indirect=True,
)
async def test_can_read_collection(shabti_user_client, shabti_collection_id):
    docs = await shabti_user_client.get_documents(shabti_collection_id)
    assert isinstance(docs, list)


@pytest.mark.parametrize(
    "shabti_user_client,shabti_collection_id",
    [
        ("testsharedread", {"username": "testadmin", "location": "private"}),
        ("testshared", {"username": "testadmin", "location": "private"}),
        ("testprivate", {"username": "testadmin", "location": "private"}),
        ("testprivate", {"username": "testadmin", "location": "shared"}),
        ("testnothing", {"username": "testadmin", "location": "shared"}),
        ("testnothing", {"username": "testadmin", "location": "private"}),
    ],
    indirect=True,
)
async def test_cannot_read_collection(shabti_user_client, shabti_collection_id):
    with pytest.raises(ShabtiAuthenticationError):
        await shabti_user_client.get_documents(shabti_collection_id)


async def ingest_document(shabti_user_client, shabti_collection_id):
    document_id = None
    async for info in shabti_user_client.insert_files(
        shabti_collection_id, [file_path]
    ):
        document_id = info.document_id
    return document_id


@pytest.mark.parametrize(
    "shabti_user_client,shabti_collection_id",
    [
        ("testadmin", {"username": "testadmin", "location": "shared"}),
        ("testadmin", {"username": "testadmin", "location": "private"}),
        ("testadmin", {"username": "testprivate", "location": "private"}),
        ("testshared", {"username": "testadmin", "location": "shared"}),
        ("testprivate", {"username": "testprivate", "location": "private"}),
    ],
    indirect=True,
)
async def test_can_ingest_document(shabti_user_client, shabti_collection_id):
    assert await ingest_document(shabti_user_client, shabti_collection_id)


@pytest.mark.parametrize(
    "shabti_user_client,shabti_collection_id",
    [
        ("testsharedread", {"username": "testadmin", "location": "private"}),
        ("testsharedread", {"username": "testadmin", "location": "shared"}),
        ("testshared", {"username": "testadmin", "location": "private"}),
        ("testprivate", {"username": "testadmin", "location": "private"}),
        ("testprivate", {"username": "testadmin", "location": "shared"}),
        ("testnothing", {"username": "testadmin", "location": "shared"}),
        ("testnothing", {"username": "testadmin", "location": "private"}),
    ],
    indirect=True,
)
async def test_cannot_ingest_document(shabti_user_client, shabti_collection_id):
    with pytest.raises(ShabtiAuthenticationError):
        await ingest_document(shabti_user_client, shabti_collection_id)


@pytest.mark.parametrize(
    "shabti_user_client,shabti_collection_id",
    [
        ("testadmin", {"username": "testadmin", "location": "shared"}),
        ("testadmin", {"username": "testadmin", "location": "private"}),
        ("testadmin", {"username": "testprivate", "location": "private"}),
        ("testshared", {"username": "testadmin", "location": "shared"}),
        ("testprivate", {"username": "testprivate", "location": "private"}),
    ],
    indirect=True,
)
async def can_delete_document(
    shabti_user_client, shabti_collection_id, shabti_document_id
):
    await shabti_user_client.delete_document(shabti_collection_id, shabti_document_id)
    documents = await shabti_user_client.get_documents(shabti_collection_id)
    assert not any(doc.document_id == shabti_document_id for doc in documents)


@pytest.mark.parametrize(
    "shabti_user_client,shabti_collection_id",
    [
        ("testsharedread", {"username": "testadmin", "location": "private"}),
        ("testsharedread", {"username": "testadmin", "location": "shared"}),
        ("testshared", {"username": "testadmin", "location": "private"}),
        ("testprivate", {"username": "testadmin", "location": "private"}),
        ("testprivate", {"username": "testadmin", "location": "shared"}),
        ("testnothing", {"username": "testadmin", "location": "shared"}),
        ("testnothing", {"username": "testadmin", "location": "private"}),
    ],
    indirect=True,
)
async def test_cannot_delete_document(
    shabti_user_client, shabti_collection_id, shabti_document_id
):
    with pytest.raises(ShabtiAuthenticationError):
        await shabti_user_client.delete_document(
            shabti_collection_id, shabti_document_id
        )


@pytest.mark.parametrize(
    "shabti_user_client,shabti_collection_id",
    [
        ("testadmin", {"username": "testadmin", "location": "shared"}),
        ("testadmin", {"username": "testadmin", "location": "private"}),
        ("testadmin", {"username": "testshared", "location": "shared"}),
        ("testadmin", {"username": "testprivate", "location": "private"}),
        ("testshared", {"username": "testadmin", "location": "shared"}),
        ("testprivate", {"username": "testprivate", "location": "private"}),
    ],
    indirect=True,
)
async def test_can_delete_collection(shabti_user_client, shabti_collection_id):
    await shabti_user_client.delete_collection(shabti_collection_id)
    collections = await shabti_user_client.get_collections()
    assert not any(
        collection.collection_id == shabti_collection_id for collection in collections
    )


@pytest.mark.parametrize(
    "shabti_user_client,shabti_collection_id",
    [
        ("testsharedread", {"username": "testadmin", "location": "shared"}),
        ("testsharedread", {"username": "testadmin", "location": "private"}),
        ("testshared", {"username": "testadmin", "location": "private"}),
        ("testprivate", {"username": "testadmin", "location": "private"}),
        ("testprivate", {"username": "testadmin", "location": "shared"}),
        ("testnothing", {"username": "testadmin", "location": "shared"}),
        ("testnothing", {"username": "testadmin", "location": "private"}),
    ],
    indirect=True,
)
async def test_cannot_delete_collection(shabti_user_client, shabti_collection_id):
    with pytest.raises(ShabtiAuthenticationError):
        await shabti_user_client.delete_collection(shabti_collection_id)
