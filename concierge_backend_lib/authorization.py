from concierge_util import load_config
from .authentication import keycloak_openid_config, get_keycloak_uma
import requests

config = load_config()


def authorize(token, resource, scope):
    if not config or "auth" not in config:
        return True
    try:
        authorized = requests.post(
            keycloak_openid_config["token_endpoint"],
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
                "audience": "concierge-auth",
                "permission": f"{resource}#{scope}",
                "response_mode": "decision",
            },
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        return authorized["result"]
    except Exception:
        return False


def create_resource(resource_name, resource_type, owner):
    keycloak_uma = get_keycloak_uma()
    keycloak_uma.resource_set_create(
        {
            "name": resource_name,
            "type": resource_type,
            "owner": owner,
            "scopes": ["create", "read", "update", "delete"],
        }
    )
