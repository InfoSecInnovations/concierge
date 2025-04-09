from keycloak import (
    KeycloakOpenID,
    KeycloakOpenIDConnection,
    KeycloakAdmin,
)
import os


def server_url():
    keycloak_host = os.getenv("KEYCLOAK_HOST", "localhost")
    return f"https://{keycloak_host}:8443"


def get_keycloak_client():
    keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
    client = KeycloakOpenID(
        server_url=server_url(),
        realm_name="concierge",
        client_id=keycloak_client_id,
        client_secret_key=keycloak_client_secret,
        verify=os.getenv("ROOT_CA"),
    )
    return client


def get_service_account_connection():
    keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
    keycloak_connection = KeycloakOpenIDConnection(
        server_url=server_url(),
        realm_name="concierge",
        client_id=keycloak_client_id,
        client_secret_key=keycloak_client_secret,
        grant_type="client_credentials",
        verify=os.getenv("ROOT_CA"),
    )
    return keycloak_connection


def get_keycloak_admin_client():
    keycloak_connection = get_service_account_connection()
    client = KeycloakAdmin(connection=keycloak_connection)
    return client


def get_keycloak_admin_openid_token():
    client = get_keycloak_client()
    token = client.token(grant_type="client_credentials")
    return token


async def get_token_info(token):
    keycloak_openid = get_keycloak_client()
    return await keycloak_openid.a_decode_token(token, validate=False)


username_cache = {}


def get_username(user_id):
    if user_id in username_cache:
        return username_cache[user_id]
    admin_client = get_keycloak_admin_client()
    user_info = admin_client.get_user(user_id)
    if "username" in user_info:
        username_cache[user_id] = user_info["username"]
        return username_cache[user_id]
    return ""
