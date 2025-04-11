from concierge_keycloak import (
    get_keycloak_client,
    get_keycloak_admin_client,
    server_url,
)
import os
from keycloak import KeycloakPostError, KeycloakAuthenticationError
from keycloak.exceptions import raise_error_from_response
import httpx
import ssl


class UnauthorizedOperationError(Exception):
    def __init__(self, message=""):
        self.message = message


async def authorize(token, resource, scope: str | None = None):
    permission = resource
    if scope:
        permission += f"#{scope}"
    async with httpx.AsyncClient(
        verify=ssl.create_default_context(cafile=os.getenv("ROOT_CA")), timeout=None
    ) as httpx_client:
        resp = await httpx_client.post(
            f"{server_url()}/realms/concierge/protocol/openid-connect/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
                "audience": "concierge-auth",
                "permission": permission,
                "response_mode": "decision",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    # this will cause us to get a new token if needed
    raise_error_from_response(resp, KeycloakPostError)
    authorized = resp.json()
    return authorized["result"]


async def create_resource(resource_name, resource_type, owner_id):
    admin_client = get_keycloak_admin_client()
    # this identifier allows us to only get name collisions if the collection has the same access permissions
    identifier = resource_type
    if resource_type == "collection:private":
        identifier = f"{identifier}_{owner_id}"
    client_id = await admin_client.a_get_client_id("concierge-auth")
    response = await admin_client.a_create_client_authz_resource(
        client_id,
        {
            "name": f"{identifier}_{resource_name}",
            "displayName": resource_name,
            "type": resource_type,
            "attributes": {"concierge_owner": [owner_id]},
            "scopes": ["read", "update", "delete"],
        },
    )
    return response["_id"]


async def list_resources(token):
    keycloak_openid = get_keycloak_client()
    try:
        response = await keycloak_openid.a_uma_permissions(token)
    except (KeycloakPostError, KeycloakAuthenticationError) as e:
        # 401 means no authorization provided, 403 means not authorized, so we can return an empty list
        if e.response_code == 401 or e.response_code == 403:
            return []
    admin_client = get_keycloak_admin_client()
    client_id = await admin_client.a_get_client_id("concierge-auth")
    resources = [
        await admin_client.a_get_client_authz_resource(client_id, resource["rsid"])
        for resource in response
    ]
    return resources


async def has_scope(token, scope):
    """check if we have any resources available with the given scope"""
    keycloak_openid = get_keycloak_client()
    try:
        response = await keycloak_openid.a_uma_permissions(token, f"#{scope}")
    except (KeycloakPostError, KeycloakAuthenticationError) as e:
        # 401 means no authorization provided, 403 means not authorized, so we can return False
        if e.response_code == 401 or e.response_code == 403:
            return False
    return len(response) != 0


async def list_permissions(token):
    keycloak_openid = get_keycloak_client()
    try:
        response = await keycloak_openid.a_uma_permissions(
            token, ["collection:private:create", "collection:shared:create"]
        )
    except (KeycloakPostError, KeycloakAuthenticationError) as e:
        # 401 means no authorization provided, 403 means not authorized, so we can return an empty set
        if e.response_code == 401 or e.response_code == 403:
            return set()
    admin_client = get_keycloak_admin_client()
    client_id = await admin_client.a_get_client_id("concierge-auth")
    resources = [
        await admin_client.a_get_client_authz_resource(client_id, resource["rsid"])
        for resource in response
    ]
    return {resource["name"] for resource in resources}


async def list_scopes(token, resource_id):
    keycloak_openid = get_keycloak_client()
    try:
        response = await keycloak_openid.a_uma_permissions(token, resource_id)
        if not len(response):
            return []
        return response[0]["scopes"]
    except (KeycloakPostError, KeycloakAuthenticationError) as e:
        # 401 means no authorization provided, 403 means not authorized, so we can return an empty list
        if e.response_code == 401 or e.response_code == 403:
            return []


async def delete_resource(resource_id):
    admin_client = get_keycloak_admin_client()
    client_id = await admin_client.a_get_client_id("concierge-auth")
    await admin_client.a_delete_client_authz_resource(client_id, resource_id)
