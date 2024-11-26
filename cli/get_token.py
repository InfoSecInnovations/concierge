from concierge_backend_lib.authentication import (
    get_keycloak_client,
    get_keycloak_admin_openid_token,
)
from concierge_backend_lib.authorization import auth_enabled


def get_token():
    if not auth_enabled:
        return {"access_token": None}
    openid_client = get_keycloak_client()
    return get_keycloak_admin_openid_token(openid_client)
