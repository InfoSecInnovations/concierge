from shabti_keycloak import get_keycloak_client, get_keycloak_admin_openid_token
from shabti_api_client import ShabtiAuthorizationClient
import os


async def get_admin_client():
    keycloak_client = get_keycloak_client()
    token = get_keycloak_admin_openid_token()
    return ShabtiAuthorizationClient(
        server_url="https://shabti:15131",
        token=token,
        keycloak_client=keycloak_client,
        verify=os.getenv("ROOT_CA"),
    )
