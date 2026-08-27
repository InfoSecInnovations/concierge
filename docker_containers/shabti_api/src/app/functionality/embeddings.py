import requests
import os
from shabti_types import EmbeddingsError, ModelNotFoundError


def get_json(response: requests.Response, action: str):
    if response.status_code >= 400:
        raise EmbeddingsError(
            message=f"{action} failed: {response.text}",
            upstream_status=response.status_code,
        )
    body = response.json()
    if "data" not in body:  # the endpoint can report errors with a 200 status
        raise EmbeddingsError(
            message=f"{action} returned no data: {response.text}",
            upstream_status=response.status_code,
        )
    return body


def create_embeddings(text):
    # don't try to do embeddings on empty values
    if not isinstance(text, list) and not text.strip():
        return None
    if not text:
        return []
    models_data = get_json(
        requests.get(f"http://{os.getenv('LLM_HOST')}:11434/models"),
        "listing models",
    )
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
    response = get_json(
        requests.post(f"http://{os.getenv('LLM_HOST')}:11434/v1/embeddings", json=data),
        "creating embeddings",
    )
    if not isinstance(text, list):
        return response["data"][0]["embedding"]
    return [x["embedding"] for x in response["data"]]
