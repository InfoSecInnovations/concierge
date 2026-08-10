from shabti_keycloak import (
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


def no_access_result(error, empty, codes=(401, 403)):
    """the result to use when Keycloak refuses a permissions request

    401 means no authorization was provided and 403 means not authorized, in both cases the
    caller simply has no access, so an empty result is the correct answer. Anything else is a
    real failure and gets raised rather than being reported as having no access
    """
    if error.response_code in codes:
        return empty
    raise error


async def authorize(token, resource, scope: str | None = None):
    permission = resource
    if scope:
        permission += f"#{scope}"
    async with httpx.AsyncClient(
        verify=ssl.create_default_context(cafile=os.getenv("ROOT_CA")), timeout=None
    ) as httpx_client:
        resp = await httpx_client.post(
            f"{server_url()}/realms/shabti/protocol/openid-connect/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
                "audience": "shabti-auth",
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
    client_id = await admin_client.a_get_client_id("shabti-auth")
    response = await admin_client.a_create_client_authz_resource(
        client_id,
        {
            "name": f"{identifier}_{resource_name}",
            "displayName": resource_name,
            "type": resource_type,
            "attributes": {"shabti_owner": [owner_id]},
            "scopes": ["read", "update", "delete"],
        },
    )
    return response["_id"]


async def list_resources(token):
    keycloak_openid = get_keycloak_client()
    try:
        response = await keycloak_openid.a_uma_permissions(token)
    except (KeycloakPostError, KeycloakAuthenticationError) as e:
        return no_access_result(e, [])
    admin_client = get_keycloak_admin_client()
    client_id = await admin_client.a_get_client_id("shabti-auth")
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
        return no_access_result(e, False)
    return len(response) != 0


async def list_permissions(token):
    keycloak_openid = get_keycloak_client()
    try:
        response = await keycloak_openid.a_uma_permissions(
            token,
            [
                "collection:private:create",
                "collection:shared:create",
                "collection:private:assign",
            ],
        )
    except (KeycloakPostError, KeycloakAuthenticationError) as e:
        return no_access_result(e, set())
    admin_client = get_keycloak_admin_client()
    client_id = await admin_client.a_get_client_id("shabti-auth")
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
        # a 401 isn't expected here because the request names a resource we already have
        return no_access_result(e, [], (403,))


async def delete_resource(resource_id):
    admin_client = get_keycloak_admin_client()
    client_id = await admin_client.a_get_client_id("shabti-auth")
    await admin_client.a_delete_client_authz_resource(client_id, resource_id)
