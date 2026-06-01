import requests
import os
import time
from shabti_types import ModelLoadInfo
from fastapi.responses import StreamingResponse
import tomllib


def load_model(model_name: str):
    print(f"loading model {model_name}")

    with open(
        "/opt/shabti_config/shabti_models.toml", "rb"
    ) as f:  # TODO: load this from configured models rather than all models
        models_data = tomllib.load(f)
    requested_model = next(
        (
            x
            for x in [*models_data["chat"], models_data["embeddings"][0]]
            if x["name"] == model_name
        ),
        None,
    )

    if not requested_model:
        raise Exception("Model is not in list of allowed models")

    def model_status():
        status = requests.get(f"http://{os.getenv('LLM_HOST')}:11434/models").json()
        model_status = next(
            (x for x in status["data"] if x["id"] == requested_model["hf"]), None
        )
        if not model_status:
            return None
        return model_status["status"]["value"]

    current_status = model_status()

    if not current_status:
        response = requests.post(
            f"http://{os.getenv('MODEL_LOADER_HOST')}:8090/api/download",
            json={"repo": requested_model["hf"]},
        ).json()
        job_id = response["id"]

        def update_status():
            return requests.get(
                f"http://{os.getenv('MODEL_LOADER_HOST')}:8090/api/jobs/{job_id}"
            ).json()

        job_data = update_status()
        while job_data["status"] not in ["completed", "failed"]:
            yield ModelLoadInfo(
                progress=job_data["progress"]["downloadedBytes"],
                total=job_data["progress"]["totalBytes"],
                model_name=model_name,
                info="downloading",
            )
            time.sleep(1)
            job_data = update_status()
        if job_data["status"] == "failed":
            raise Exception("Model failed to load")

    current_status = model_status()

    if current_status == "loaded":
        print(f"Model {model_name} is already loaded")
        return

    if current_status == "unloaded":
        requests.post(
            f"http://{os.getenv('LLM_HOST')}:11434/models/load",
            json={"model": requested_model["hf"]},
        )

    while current_status != "loaded":
        yield ModelLoadInfo(
            progress=1, total=1, model_name=model_name, info=current_status
        )
        time.sleep(1)
        current_status = model_status()
        if not current_status:
            raise Exception("Model not found in Llama.cpp")

    print(f"Loaded model {model_name}")


def load_model_stream(model_name: str):
    return StreamingResponse(load_model(model_name))
