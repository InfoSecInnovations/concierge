from shabti_keycloak import get_keycloak_admin_client, get_token_info

# Keycloak drops user attributes that aren't declared in the realm's user profile, so this one is
# declared in the realm import file
CHAT_MODEL_ATTRIBUTE = "shabti_chat_model"


async def user_id(credentials: str) -> str:
    return (await get_token_info(credentials))["sub"]


async def get_user_chat_model(credentials: str) -> str | None:
    admin_client = get_keycloak_admin_client()
    user = await admin_client.a_get_user(await user_id(credentials))
    values = user.get("attributes", {}).get(CHAT_MODEL_ATTRIBUTE)
    return values[0] if values else None


async def set_user_chat_model(credentials: str, model_name: str):
    admin_client = get_keycloak_admin_client()
    id = await user_id(credentials)
    user = await admin_client.a_get_user(id)
    # updating a user replaces its whole attribute map, so we merge into what's already there
    attributes = user.get("attributes", {})
    attributes[CHAT_MODEL_ATTRIBUTE] = [model_name]
    await admin_client.a_update_user(id, {"attributes": attributes})
