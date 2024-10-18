from .authentication import (
    keycloak_openid_config,
    get_keycloak_uma,
    get_keycloak_client,
    get_keycloak_admin_client,
)
import requests


def authorize(token, resource, scope: str | None = None):
    try:
        permission = resource
        if scope:
            permission += f"#{scope}"
        authorized = requests.post(
            keycloak_openid_config["token_endpoint"],
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
                "audience": "concierge-auth",
                "permission": permission,
                "response_mode": "decision",
            },
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        return authorized["result"]
    except Exception:
        return False


def create_resource(resource_name, resource_type, owner):
    keycloak_uma = get_keycloak_uma()
    response = keycloak_uma.resource_set_create(
        {
            "name": resource_name,
            "displayName": resource_name,
            "type": resource_type,
            "owner": owner,
            "scopes": ["read", "update", "delete"],
        }
    )
    return response["_id"]


def list_resources(token):
    keycloak_openid = get_keycloak_client()
    response = keycloak_openid.uma_permissions(token)
    admin_client = get_keycloak_admin_client()
    client_id = admin_client.get_client_id("concierge-auth")
    resources = [
        admin_client.get_client_authz_resource(client_id, resource["rsid"])
        for resource in response
    ]
    return resources


def delete_resource(resource_id):
    keycloak_uma = get_keycloak_uma()
    keycloak_uma.resource_set_delete(resource_id)
