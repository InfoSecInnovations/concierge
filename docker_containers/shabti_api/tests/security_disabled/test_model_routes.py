import pytest
from ...src.app.functionality.models import (
    get_models,
    load_model,
    model_status,
    unload_models,
)


def statuses(models_data):
    return {x["id"]: model_status(x) for x in models_data["data"]}


async def test_get_models_with_tags(shabti_client):
    response = shabti_client.get("/models", params={"tags": ["chat"]})
    assert response.status_code == 200
    assert all("tags" in x and "chat" in x["tags"] for x in response.json()["data"])


async def test_get_chat_model(shabti_client, loaded_chat_model):
    response = shabti_client.get("/models/chat")
    assert response.status_code == 200
    assert response.json()["model_name"] == loaded_chat_model


# we can't size concurrent models against the available hardware yet, so only one chat
# model may be loaded at a time and selecting another one has to swap it out
async def test_loading_a_chat_model_unloads_the_other_ones(
    shabti_client, loaded_chat_model
):
    chat_models = (await get_models(tags=["chat"]))["data"]
    other = next((x for x in chat_models if x["id"] != loaded_chat_model), None)
    if not other:
        pytest.skip("only one chat model is installed")
    async for _ in load_model(other["id"]):
        pass
    chat_statuses = statuses(await get_models(tags=["chat"]))
    assert chat_statuses[other["id"]] == "loaded"
    assert chat_statuses[loaded_chat_model] == "unloaded"


# chat and embeddings are separate categories, so swapping one must leave the other alone
async def test_loading_a_chat_model_keeps_the_embeddings_model(
    shabti_client, loaded_chat_model
):
    embeddings_models = (await get_models(tags=["embeddings"]))["data"]
    if not embeddings_models:
        pytest.skip("no embeddings model is installed")
    embeddings_id = embeddings_models[0]["id"]
    async for _ in load_model(embeddings_id):
        pass
    async for _ in load_model(loaded_chat_model):
        pass
    assert statuses(await get_models())[embeddings_id] == "loaded"


# asking which chat model is in use answers null rather than erroring when there isn't one
async def test_get_chat_model_without_a_loaded_chat_model(
    shabti_client, loaded_chat_model
):
    chat_models = (await get_models(tags=["chat"]))["data"]
    async for _ in unload_models([x["id"] for x in chat_models]):
        pass
    try:
        response = shabti_client.get("/models/chat")
        assert response.status_code == 200
        assert response.json() is None
    finally:
        async for _ in load_model(loaded_chat_model):
            pass
