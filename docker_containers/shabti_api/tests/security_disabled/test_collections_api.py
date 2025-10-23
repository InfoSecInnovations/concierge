import os
from ...src.app.document_collections import (
    delete_collection,
    get_collections,
    get_documents,
)
import asyncio
from ...src.app.ingesting import insert_document
from ...src.app.loading import load_file
from shabti_util import auth_enabled

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)

collection_lookup = {}
collection_name = "test_collection"


def test_auth_setting():
    assert not auth_enabled()


def test_create_collection(shabti_client):
    response = shabti_client.post(
        "/collections", json={"collection_name": collection_name}
    )
    assert response.status_code == 201
    collection_id = response.json()["collection_id"]
    assert collection_id
    collection_lookup[collection_name] = collection_id


def test_list_collections(shabti_client):
    response = shabti_client.get("/collections")
    assert response.status_code == 200
    assert next(
        (
            collection_info
            for collection_info in response.json()
            if collection_info["collection_id"] == collection_lookup[collection_name]
        )
    )


async def test_insert_documents(shabti_client):
    response = shabti_client.post(
        f"/collections/{collection_lookup[collection_name]}/documents/files",
        files=[("files", open(file_path, "rb"))],
    )
    assert response.status_code == 200
    docs = await get_documents(None, collection_lookup[collection_name])
    assert len(docs)


async def test_insert_urls(shabti_client):
    url = "https://en.wikipedia.org/wiki/Generative_artificial_intelligence"
    response = shabti_client.post(
        f"/collections/{collection_lookup[collection_name]}/documents/urls", json=[url]
    )
    assert response.status_code == 200
    docs = await get_documents(None, collection_lookup[collection_name])
    assert next((doc for doc in docs if doc.source == url))


async def test_delete_document(shabti_client):
    with open(file_path, "rb") as f:
        doc = load_file(f, filename)
        binary = f.read()
    async for ingest_info in insert_document(
        None, collection_lookup[collection_name], doc, binary
    ):
        pass
    response = shabti_client.delete(
        f"/collections/{collection_lookup[collection_name]}/documents/{ingest_info.document_id}"
    )
    assert response.status_code == 200
    docs = await get_documents(None, collection_lookup[collection_name])
    assert not any(doc.document_id == ingest_info.document_id for doc in docs)


async def test_delete_collection(shabti_client):
    response = shabti_client.delete(
        f"/collections/{collection_lookup[collection_name]}"
    )
    assert response.status_code == 200
    collections = await get_collections(None)
    response_json = response.json()
    assert not any(
        collection.collection_id == response_json["collection_id"]
        for collection in collections
    )


async def test_create_collection_after_delete(shabti_client):
    response = shabti_client.post(
        "/collections", json={"collection_name": collection_name}
    )
    assert response.status_code == 201
    collection_id = response.json()["collection_id"]
    assert collection_id
    collection_lookup[collection_name] = collection_id


async def clean_up_collections():
    collections = await get_collections(None)
    for collection in collections:
        try:
            await delete_collection(None, collection.collection_id)
        except Exception:  # we're not trying to test collection getting and deletion here so just do our best to clean up!
            pass


def teardown_module():
    asyncio.run(clean_up_collections())
