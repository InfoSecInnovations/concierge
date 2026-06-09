import requests
import os
import tomllib


def create_embeddings(text):
    # don't try to do embeddings on empty values
    if not isinstance(text, list) and not text.strip():
        return None
    if not text:
        return []
    with open("/opt/shabti_config/shabti_models.toml", "rb") as f:
        models_data = tomllib.load(f)
    model = models_data["embeddings"]
    data = {
        "model": model["hf"],
        "input": text,
        "encoding_format": "float",
    }
    response = requests.post(
        f"http://{os.getenv('LLM_HOST')}:11434/v1/embeddings", json=data
    ).json()
    if not isinstance(text, list):
        return response["data"][0]["embedding"]
    return [x["embedding"] for x in response["data"]]
