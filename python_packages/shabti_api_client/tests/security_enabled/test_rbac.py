import os
import pytest
from shabti_api_client import ShabtiAuthenticationError
import secrets
from .lib import get_admin_client

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
    admin_client = await get_admin_client()
    collections = await admin_client.get_collections()
    assert next(
        (
            collection_info
            for collection_info in collections
            if collection_info.collection_id == collection_id
            and collection_info.collection_name == collection_name
        ),
        None,
    )


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
    admin_client = await get_admin_client()
    collections = await admin_client.get_collections()
    assert not any(
        collection_info.collection_name == collection_name
        for collection_info in collections
    )


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
    collections = await shabti_user_client.get_collections()
    assert next(
        (
            collection_info
            for collection_info in collections
            if collection_info.collection_id == shabti_collection_id
        ),
        None,
    )


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
    collections = await shabti_user_client.get_collections()
    assert not any(
        collection_info.collection_id == shabti_collection_id
        for collection_info in collections
    )


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
    document_id = await ingest_document(shabti_user_client, shabti_collection_id)
    assert document_id
    admin_client = await get_admin_client()
    documents = await admin_client.get_documents(shabti_collection_id)
    assert next(
        (
            doc
            for doc in documents
            if doc.filename == filename and doc.document_id == document_id
        ),
        None,
    )


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
    admin_client = await get_admin_client()
    documents = await admin_client.get_documents(shabti_collection_id)
    assert not any(doc.filename == filename for doc in documents)


url = "https://example.com"


async def ingest_url(shabti_user_client, shabti_collection_id):
    document_id = None
    async for info in shabti_user_client.insert_urls(shabti_collection_id, [url]):
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
async def test_can_ingest_url(shabti_user_client, shabti_collection_id):
    document_id = await ingest_url(shabti_user_client, shabti_collection_id)
    assert document_id
    admin_client = await get_admin_client()
    documents = await admin_client.get_documents(shabti_collection_id)
    assert next(
        (
            doc
            for doc in documents
            if doc.source == url and doc.document_id == document_id
        ),
        None,
    )


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
async def test_cannot_ingest_url(shabti_user_client, shabti_collection_id):
    with pytest.raises(ShabtiAuthenticationError):
        await ingest_url(shabti_user_client, shabti_collection_id)
    admin_client = await get_admin_client()
    documents = await admin_client.get_documents(shabti_collection_id)
    assert not any(doc.source == url for doc in documents)


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
    admin_client = await get_admin_client()
    documents = await admin_client.get_documents(shabti_collection_id)
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
    admin_client = await get_admin_client()
    documents = await admin_client.get_documents(shabti_collection_id)
    assert next(
        (doc for doc in documents if doc.document_id == shabti_document_id), None
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
    admin_client = await get_admin_client()
    collections = await admin_client.get_collections()
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
    admin_client = await get_admin_client()
    collections = await admin_client.get_collections()
    assert next(
        (
            collection_info
            for collection_info in collections
            if collection_info.collection_id == shabti_collection_id
        ),
        None,
    )
