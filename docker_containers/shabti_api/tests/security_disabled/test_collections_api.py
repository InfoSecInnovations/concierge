import os
from ...src.app.document_collections import (
    get_collections,
    get_documents,
)
from shabti_util import auth_enabled
import secrets

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


def test_auth_setting():
    assert not auth_enabled()


async def test_create_collection(shabti_client):
    collection_name = secrets.token_hex(8)
    response = shabti_client.post(
        "/collections", json={"collection_name": collection_name}
    )
    assert response.status_code == 201
    collection_id = response.json()["collection_id"]
    assert collection_id
    # after checking we got the expected type of response, also check the collection actually exists
    collections = await get_collections(None)
    assert next(
        collection_info
        for collection_info in collections
        if collection_info.collection_id == collection_id
        and collection_info.collection_name == collection_name
    )


async def test_list_collections(shabti_client, shabti_collection_id):
    response = shabti_client.get("/collections")
    assert response.status_code == 200
    assert next(
        (
            collection_info
            for collection_info in response.json()
            if collection_info["collection_id"] == shabti_collection_id
        ),
        None,
    )


async def test_insert_documents(shabti_client, shabti_collection_id):
    response = shabti_client.post(
        f"/collections/{shabti_collection_id}/documents/files",
        files=[("files", open(file_path, "rb"))],
    )
    assert response.status_code == 200
    docs = await get_documents(None, shabti_collection_id)
    assert next((doc for doc in docs if doc.filename == filename), None)


async def test_insert_urls(shabti_client, shabti_collection_id):
    url = "https://en.wikipedia.org/wiki/Generative_artificial_intelligence"
    response = shabti_client.post(
        f"/collections/{shabti_collection_id}/documents/urls", json=[url]
    )
    assert response.status_code == 200
    docs = await get_documents(None, shabti_collection_id)
    assert next((doc for doc in docs if doc.source == url), None)


async def test_delete_document(shabti_client, shabti_collection_id, shabti_document_id):
    docs = await get_documents(None, shabti_collection_id)
    # test the document is actually there before deleting it
    assert next((doc for doc in docs if doc.document_id == shabti_document_id), None)
    response = shabti_client.delete(
        f"/collections/{shabti_collection_id}/documents/{shabti_document_id}"
    )
    assert response.status_code == 200
    docs = await get_documents(None, shabti_collection_id)
    assert not any(doc.document_id == shabti_document_id for doc in docs)


async def test_delete_collection(shabti_client, shabti_collection_id):
    response = shabti_client.delete(f"/collections/{shabti_collection_id}")
    assert response.status_code == 200
    collections = await get_collections(None)
    response_json = response.json()
    assert not any(
        collection.collection_id == response_json["collection_id"]
        for collection in collections
    )
