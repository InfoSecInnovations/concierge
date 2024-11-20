import requests
from keycloak import (
    KeycloakOpenID,
    KeycloakOpenIDConnection,
    KeycloakUMA,
    KeycloakAdmin,
)
import os
from dotenv import load_dotenv
import traceback
import urllib3


urllib3.disable_warnings()


def server_url():
    load_dotenv()
    keycloak_host = os.getenv("KEYCLOAK_HOST", "localhost")
    return f"https://{keycloak_host}:8443"


def keycloak_openid_config():
    # this disables TLS verification and warning
    session = requests.Session()
    session.verify = False
    return session.get(
        f"{server_url()}/realms/concierge/.well-known/openid-configuration"
    ).json()


def get_keycloak_client():
    load_dotenv()
    keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
    client = KeycloakOpenID(
        server_url=server_url(),
        realm_name="concierge",
        client_id=keycloak_client_id,
        client_secret_key=keycloak_client_secret,
        verify=False,
    )
    return client


def get_service_account_connection():
    load_dotenv()
    keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
    keycloak_connection = KeycloakOpenIDConnection(
        server_url=server_url(),
        realm_name="concierge",
        client_id=keycloak_client_id,
        client_secret_key=keycloak_client_secret,
        grant_type="client_credentials",
        verify=False,
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


def execute_with_token(token, func):
    try:
        func(token)
        return token
    except Exception:
        keycloak_openid = get_keycloak_client()
        token = keycloak_openid.refresh_token(token["refresh_token"])
        func(token)
        return token


async def execute_async_with_token(token, func):
    try:
        try:
            await func(token)
            return token
        except Exception:
            keycloak_openid = get_keycloak_client()
            token = await keycloak_openid.a_refresh_token(token["refresh_token"])
            await func(token)
            return token
    except Exception:
        traceback.print_exc()
        raise


async def get_async_result_with_token(token, func):
    try:
        try:
            result = await func(token)
            return (token, result)
        except Exception:
            keycloak_openid = get_keycloak_client()
            token = await keycloak_openid.a_refresh_token(token["refresh_token"])
            result = await func(token)
            return (token, result)
    except Exception:
        traceback.print_exc()
        raise
