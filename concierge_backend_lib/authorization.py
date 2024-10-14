from concierge_util import load_config
from .authentication import keycloak_openid_config
import requests

config = load_config()


def authorize(token, resource, scope):
    if "auth" not in config:
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
