import requests
from keycloak import (
    KeycloakOpenID,
    KeycloakOpenIDConnection,
    KeycloakUMA,
    KeycloakAdmin,
)
import os
from dotenv import load_dotenv

load_dotenv()
KEYCLOAK_HOST = os.getenv("KEYCLOAK_HOST", "localhost")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")

# TODO: select HTTPS if enabled
server_url = f"http://{KEYCLOAK_HOST}:8080"


def keycloak_openid_config():
    requests.get(
        f"{server_url}/realms/concierge/.well-known/openid-configuration"
    ).json()


def get_keycloak_client():
    client = KeycloakOpenID(
        server_url=server_url,
        realm_name="concierge",
        client_id=KEYCLOAK_CLIENT_ID,
        client_secret_key=KEYCLOAK_CLIENT_SECRET,
    )
    return client


def get_service_account_connection():
    keycloak_connection = KeycloakOpenIDConnection(
        server_url=server_url,
        realm_name="concierge",
        client_id=KEYCLOAK_CLIENT_ID,
        client_secret_key=KEYCLOAK_CLIENT_SECRET,
        grant_type="client_credentials",
    )
    return keycloak_connection


def get_keycloak_uma():
    keycloak_connection = get_service_account_connection()
    keycloak_uma = KeycloakUMA(connection=keycloak_connection)
    return keycloak_uma


def get_keycloak_admin_client():
    keycloak_connection = get_service_account_connection()
    client = KeycloakAdmin(connection=keycloak_connection)
    return client


def get_token_info(token):
    keycloak_openid = get_keycloak_client()
    return keycloak_openid.decode_token(token, validate=False)


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
