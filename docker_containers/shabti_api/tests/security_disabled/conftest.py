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
import pytest_asyncio


@pytest_asyncio.fixture(loop_scope="session", autouse=True, scope="session")
async def shabti_client():
    load_env()
    while True:
        try:
            if check_opensearch():
                break
        except ConnectionError:
            continue
    yield TestClient(create_app())
    collections = await get_collections(None)
    for collection in collections:
        try:
            await delete_collection(None, collection.collection_id)
        except Exception:  # we're not trying to test collection getting and deletion here so just do our best to clean up!
            pass


@pytest_asyncio.fixture(scope="function")
async def shabti_collection_id():
    collection = await create_collection(None, secrets.token_hex(8))
    yield collection.collection_id
    try:
        await delete_collection(None, collection.collection_id)
    except Exception:  # collection may have already been deleted by the test
        pass
