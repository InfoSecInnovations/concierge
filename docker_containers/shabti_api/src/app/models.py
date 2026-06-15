import requests
import os
import time
from shabti_types import ModelLoadInfo, ModelNotFoundError
import tomllib


def get_model_id(model_name: str):
    with open("/opt/shabti_config/shabti_models.toml", "rb") as f:
        models_data = tomllib.load(f)
    requested_model = next(
        (
            x
            for x in [*models_data["chat"], models_data["embeddings"]]
            if x["name"] == model_name
        ),
        None,
    )
    if not requested_model:
        raise ModelNotFoundError(model=model_name)
    return requested_model["hf"]


def load_model(model_name: str):
    print(f"loading model {model_name}")

    model_id = get_model_id(model_name)

    def model_status():
        status = requests.get(
            f"http://{os.getenv('LLM_HOST')}:11434/models?reload=1"
        ).json()
        model_status = next((x for x in status["data"] if x["id"] == model_id), None)
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
            json={"model": model_id},
        )

    while current_status != "loaded":
        yield ModelLoadInfo(
            progress=0, total=1, model_name=model_name, info=current_status
        )
        time.sleep(1)
        current_status = model_status()
        if not current_status:
            raise Exception("Model not found in Llama.cpp")

    print(f"Loaded model {model_name}")
