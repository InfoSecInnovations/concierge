import pytest_asyncio
import requests
import os
from shabti_keycloak import get_keycloak_client
from shabti_api_client import ShabtiAuthorizationClient
import secrets
from .lib import get_admin_client

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def shabti_instance():
    while True:
        try:
            requests.get("https://shabti:15131", verify=os.getenv("ROOT_CA"))
            break
        except Exception:
            continue
    yield
    client = await get_admin_client()
    for collection in await client.get_collections():
        try:
            await client.delete_collection(collection.collection_id)
        except Exception:
            pass


@pytest_asyncio.fixture(scope="function")
async def shabti_user_client(request):
    keycloak_client = get_keycloak_client()
    token = await keycloak_client.a_token(username=request.param, password="test")
    yield ShabtiAuthorizationClient(
        server_url="https://shabti:15131",
        token=token,
        keycloak_client=keycloak_client,
        verify=os.getenv("ROOT_CA"),
    )


@pytest_asyncio.fixture(scope="function")
async def shabti_collection_id(request):
    client = await get_admin_client()
    collection_id = await client.create_collection(
        secrets.token_hex(8), request.param["location"], request.param["username"]
    )
    yield collection_id
    try:
        await client.delete_collection(collection_id)
    except Exception:  # the collection may have already been deleted by a test
        pass


@pytest_asyncio.fixture(scope="function")
async def shabti_document_id(shabti_collection_id):
    client = await get_admin_client()
    document_id = None
    async for info in client.insert_files(shabti_collection_id, [file_path]):
        document_id = info.document_id
    yield document_id
