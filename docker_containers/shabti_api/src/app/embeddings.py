import requests
import os


def create_embeddings(text):
    data = {
        "model": "paraphrase-multilingual",
        "input": text,
        "encoding_format": "float",
    }
    response = requests.post(
        f"http://{os.getenv("LLM_HOST")}:11434/v1/embeddings", json=data
    ).json()
    return [x["embedding"] for x in response["data"]]
