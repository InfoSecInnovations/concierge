from shabti_keycloak import get_keycloak_client
import pytest


@pytest.mark.parametrize(
    "shabti_collection_id",
    [
        {"username": "testadmin", "location": "private"},
    ],
    indirect=True,
)
def test_can_access_files_route(
    shabti_client, shabti_collection_id, shabti_document_id
):
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token("testadmin", "test")
    response = shabti_client.get(
        f"/files/{shabti_collection_id}/{shabti_document_id}",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "shabti_collection_id",
    [
        {"username": "testadmin", "location": "private"},
    ],
    indirect=True,
)
def test_other_user_cannot_access_files_route(
    shabti_client, shabti_collection_id, shabti_document_id
):
    keycloak_client = get_keycloak_client()
    token = keycloak_client.token("testshared", "test")
    response = shabti_client.get(
        f"/files/{shabti_collection_id}/{shabti_document_id}",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert response.status_code == 403
