import requests
from shabti_api_client import ShabtiClient
import pytest_asyncio
import secrets
import os

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


@pytest_asyncio.fixture(loop_scope="session", autouse=True, scope="session")
async def shabti_client():
    while True:
        try:
            requests.get("http://shabti:15131")
            break
        except Exception:
            continue
    yield ShabtiClient("http://shabti:15131")


@pytest_asyncio.fixture(scope="function")
async def shabti_collection_id(shabti_client):
    collection_id = await shabti_client.create_collection(secrets.token_hex(8))
    yield collection_id
    try:
        await shabti_client.delete_collection(collection_id)
    except Exception:  # collection may have been deleted by a test
        pass


@pytest_asyncio.fixture(scope="function")
async def shabti_document_id(shabti_client, shabti_collection_id):
    document_id = None
    async for info in shabti_client.insert_files(shabti_collection_id, [file_path]):
        document_id = info.document_id
    yield document_id
