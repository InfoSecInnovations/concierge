from fastapi.testclient import TestClient
from app.app import app
import os
from app.document_collections import delete_collection, get_collections
import asyncio
from isi_util.list_util import find

client = TestClient(app)

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)

collection_lookup = {}


def test_create_collection():
    collection_name = "test_collection"
    response = client.post("/collections", json={"collection_name": collection_name})
    assert response.status_code == 200
    collection_id = response.json()["collection_id"]
    assert collection_id
    collection_lookup[collection_name] = collection_id


async def test_delete_collection():
    response = client.delete(f"/collections/{collection_lookup["test_collection"]}")
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
