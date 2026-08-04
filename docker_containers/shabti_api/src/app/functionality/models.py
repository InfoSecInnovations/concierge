import requests
import os
import httpx
from shabti_types import ModelLoadInfo, ModelNotFoundError
from httpx_sse import aconnect_sse
import json


async def get_models(tags: list[str] | None = None):
    async with httpx.AsyncClient() as client:
        res = (await client.get(f"http://{os.getenv('LLM_HOST')}:11434/models")).json()
    if tags:
        res["data"] = [
            x for x in res["data"] if any(tag in tags for tag in x.get("tags", []))
        ]
    return res


# takes the output of get_models so the caller can reuse a list it has already fetched
# this function does not check the other tags and will use whichever data is passed in
def default_model_id(models_data) -> str | None:
    models = models_data["data"]
    if not models:
        return None
    # if no model is tagged as the default we just use the first one available
    return next(
        (x["id"] for x in models if "default" in x.get("tags", [])), models[0]["id"]
    )


async def get_default_chat_model() -> str:
    model_id = default_model_id(await get_models(tags=["chat"]))
    if not model_id:
        raise ModelNotFoundError(message="No chat model is available")
    return model_id


async def load_model(model_name: str):
    print(f"loading model {model_name}")

    def model_status():
        status = requests.get(
            f"http://{os.getenv('LLM_HOST')}:11434/models?reload=1"
        ).json()
        model_status = next((x for x in status["data"] if x["id"] == model_name), None)
        if not model_status:
            return None
        return model_status["status"]["value"]

    current_status = model_status()

    if current_status == "loaded":
        print(f"Model {model_name} is already loaded")
        return

    if current_status == "unloaded":
        requests.post(
            f"http://{os.getenv('LLM_HOST')}:11434/models/load",
            json={"model": model_name},
        )

    async with httpx.AsyncClient(timeout=None) as httpx_client:
        async with aconnect_sse(
            httpx_client,
            "GET",
            f"http://{os.getenv('LLM_HOST')}:11434/models/sse",
        ) as event_source:
            async for sse in event_source.aiter_sse():
                json_data = json.loads(sse.data)
                print(json_data)
                if json_data["model"] != model_name:
                    continue
                status = (
                    "data" in json_data
                    and "status" in json_data["data"]
                    and json_data["data"]["status"]
                )
                if json_data["event"] == "status_change":
                    if status == "loaded":
                        break
                    if status == "unloaded":
                        raise Exception("Model not loaded")
                if status == "loading":
                    yield ModelLoadInfo(
                        progress=json_data["data"]["progress"]["value"],
                        total=1,
                        model_name=model_name,
                        info=f"{status} {json_data['data']['progress']['current']}",
                    )

    print(f"Loaded model {model_name}")
