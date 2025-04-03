from fastapi.testclient import TestClient
from app.app import app
import os
from app.document_collections import delete_collection, get_collections, get_documents
import asyncio
from isi_util.list_util import find
from app.ingesting import insert_document
from app.loading import load_file

client = TestClient(app)

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)

collection_lookup = {}
collection_name = "test_collection"


def test_create_collection():
    response = client.post("/collections", json={"collection_name": collection_name})
    assert response.status_code == 201
    collection_id = response.json()["collection_id"]
    assert collection_id
    collection_lookup[collection_name] = collection_id


def test_list_collections():
    response = client.get("/collections")
    assert response.status_code == 200
    assert find(
        response.json(),
        lambda x: x["collection_id"] == collection_lookup[collection_name],
    )


async def test_insert_documents():
    response = client.post(
        f"/collections/{collection_lookup[collection_name]}/documents/files",
        files=[("files", open(file_path, "rb"))],
    )
    assert response.status_code == 200
    docs = await get_documents(None, collection_lookup[collection_name])
    assert len(docs)


async def test_insert_urls():
    url = "https://en.wikipedia.org/wiki/Generative_artificial_intelligence"
    response = client.post(
        f"/collections/{collection_lookup[collection_name]}/documents/urls", json=[url]
    )
    assert response.status_code == 200
    docs = await get_documents(None, collection_lookup[collection_name])
    assert find(docs, lambda x: x.source == url)


async def test_delete_document():
    doc = load_file(file_path, filename)
    with open(file_path, "rb") as f:
        binary = f.read()
    async for ingest_info in insert_document(
        None, collection_lookup[collection_name], doc, binary
    ):
        pass
    response = client.delete(
        f"/collections/{collection_lookup[collection_name]}/documents/plaintext/{ingest_info.document_id}"
    )
    assert response.status_code == 200
    docs = await get_documents(None, collection_lookup[collection_name])
    assert not find(docs, lambda x: x.document_id == ingest_info.document_id)


async def test_delete_collection():
    response = client.delete(f"/collections/{collection_lookup[collection_name]}")
    assert response.status_code == 200
    collections = await get_collections(None)
    assert not find(
        collections, lambda x: x.collection_id == response.json()["collection_id"]
    )


async def clean_up_collections():
    for collection_id in collection_lookup.values():
        try:
            await delete_collection(None, collection_id)
        except Exception:  # some collections may have been deleted by tests so it doesn't matter if this fails
            pass


def teardown_module():
    asyncio.run(clean_up_collections())
