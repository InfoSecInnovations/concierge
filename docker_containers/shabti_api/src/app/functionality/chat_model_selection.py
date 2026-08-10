from .models import active_chat_model, default_model_id, get_models
from .user_settings import get_user_chat_model, set_user_chat_model

# credentials are None when security is disabled, in which case Shabti is treated as a single
# instance and the loaded model, rather than a stored preference, is the selection


async def chat_model_selection(credentials: str | None) -> str | None:
    models = await get_models(tags=["chat"])
    if credentials:
        stored = await get_user_chat_model(credentials)
        # the stored model may have been removed from the installation since it was chosen
        if stored and any(x["id"] == stored for x in models["data"]):
            return stored
    elif loaded := active_chat_model(models):
        return loaded
    return default_model_id(models)


async def set_chat_model_selection(credentials: str | None, model_name: str):
    if credentials:
        await set_user_chat_model(credentials, model_name)
