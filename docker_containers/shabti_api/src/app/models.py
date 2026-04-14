import requests
import os
import time
from isi_util.async_single import asyncify


def load_model_sync(model_name: str):
    print(f"loading model {model_name}")

    def model_status():
        status = requests.get(f"http://{os.getenv("LLM_HOST")}:11434/models").json()
        model_status = next(x for x in status["data"] if x["id"] == model_name)
        if not model_status:
            raise Exception("Model is not in list")
        return model_status["status"]["value"]

    current_status = model_status()
    if current_status == "loaded":
        print(f"Model {model_name} is already loaded")
        return

    if current_status == "unloaded":
        requests.post(
            f"http://{os.getenv("LLM_HOST")}:11434/models/load",
            json={"model": model_name},
        )

    while model_status() != "loaded":
        time.sleep(5)

    print(f"Loaded model {model_name}")


async def load_model(model_name: str):
    return asyncify(load_model_sync, model_name)
