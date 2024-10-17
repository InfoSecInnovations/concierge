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

keycloak_config = {
    # TODO: select HTTPS if enabled
    # TODO: select keycloak host if running in container
    "url": "http://localhost:8080/realms/concierge/.well-known/openid-configuration",
    "display_name": "Keycloak",
    "id_env_var": "KEYCLOAK_CLIENT_ID",
    "roles_key": "roles",
    "secret_env_var": "KEYCLOAK_CLIENT_SECRET",
}

keycloak_openid_config = requests.get(keycloak_config["url"]).json()

# TODO: select HTTPS if enabled
# TODO: select keycloak host if running in container
server_url = "http://localhost:8080"


def get_keycloak_client():
    client = KeycloakOpenID(
        server_url=server_url,
        realm_name="concierge",
        client_id=os.getenv(keycloak_config["id_env_var"]),
        client_secret_key=os.getenv(keycloak_config["secret_env_var"]),
    )
    return client


def get_service_account_connection():
    keycloak_connection = KeycloakOpenIDConnection(
        server_url=server_url,
        realm_name="concierge",
        client_id=os.getenv(keycloak_config["id_env_var"]),
        client_secret_key=os.getenv(keycloak_config["secret_env_var"]),
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
