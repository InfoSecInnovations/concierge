from app.app import app
from fastapi.testclient import TestClient
from .lib import create_collection_for_user, ingest_document
import asyncio
from app.authentication import get_keycloak_client
import pytest
from keycloak import KeycloakPostError

client = TestClient(app)

collection_id = None
doc_id = None


async def create_collection_and_doc():
    global collection_id
    global doc_id
    collection_id = await create_collection_for_user(
        "testadmin", "private", "test_docs"
    )
    doc_id = await ingest_document("testadmin", collection_id)


def setup_module():
    asyncio.run(create_collection_and_doc())


def test_can_access_files_route():
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token("testadmin", "test")
    response = client.get(
        f"/files/{collection_id}/{doc_id}",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert response.status_code == 200


def test_other_user_cannot_access_files_route():
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token("testshared", "test")
    with pytest.raises(KeycloakPostError):
        client.get(
            f"/files/{collection_id}/{doc_id}",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
