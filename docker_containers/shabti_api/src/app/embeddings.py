import requests
import os
from shabti_types import ModelNotFoundError


def create_embeddings(text):
    # don't try to do embeddings on empty values
    if not isinstance(text, list) and not text.strip():
        return None
    if not text:
        return []
    models_data = requests.get(f"http://{os.getenv('LLM_HOST')}:11434/models").json()
    embeddings_model_data = next(
        (x for x in models_data["data"] if "embeddings" in x["tags"]), None
    )
    if not embeddings_model_data:
        raise ModelNotFoundError()
    data = {
        "model": embeddings_model_data["id"],
        "input": text,
        "encoding_format": "float",
    }
    response = requests.post(
        f"http://{os.getenv('LLM_HOST')}:11434/v1/embeddings", json=data
    ).json()
    if not isinstance(text, list):
        return response["data"][0]["embedding"]
    return [x["embedding"] for x in response["data"]]
