import requests
import os
import time
from shabti_types import ModelLoadInfo
from fastapi.responses import StreamingResponse


def load_model(model_name: str):
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

    # TODO: real progress
    current = 0
    while model_status() != "loaded":
        yield ModelLoadInfo(
            progress=current,
            total=current + 1,
            model_name=model_name,
        )
        time.sleep(5)
        current += 1

    print(f"Loaded model {model_name}")


def load_model_stream(model_name: str):
    return StreamingResponse(load_model(model_name))
