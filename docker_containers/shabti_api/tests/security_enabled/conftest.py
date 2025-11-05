import pytest_asyncio
from ...src.app.status import check_opensearch
from ...src.load_dotenv import load_env
from ...src.app.app import create_app
from fastapi.testclient import TestClient
from ...src.app.document_collections import (
    create_collection,
    delete_collection,
    get_collections,
)
import secrets
from shabti_keycloak import (
    get_keycloak_admin_openid_token,
)
from ...src.app.ingesting import insert_document
import os
from ...src.app.loading import load_file


filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


@pytest_asyncio.fixture(loop_scope="session", autouse=True, scope="session")
async def shabti_client():
    load_env()
    while True:
        try:
            # TODO: ping Keycloak too?
            if check_opensearch():
                break
        except ConnectionError:
            continue
    yield TestClient(create_app())
    token = get_keycloak_admin_openid_token()
    collections = await get_collections(token["access_token"])
    for collection in collections:
        await delete_collection(token["access_token"], collection.collection_id)


@pytest_asyncio.fixture(scope="function")
async def shabti_collection_id(request):
    token = get_keycloak_admin_openid_token()
    collection = await create_collection(
        token["access_token"],
        secrets.token_hex(8),
        request.param["location"],
        request.param["username"],
    )
    yield collection.collection_id
    try:
        await delete_collection(token["access_token"], collection.collection_id)
    except Exception:  # collection may have already been deleted by the test
        pass


@pytest_asyncio.fixture(scope="function")
async def shabti_document_id(shabti_collection_id):
    token = get_keycloak_admin_openid_token()
    with open(file_path, "rb") as f:
        doc = load_file(f, filename)
        binary = f.read()
    async for ingest_info in insert_document(
        token["access_token"], shabti_collection_id, doc, binary
    ):
        pass
    yield ingest_info.document_id
