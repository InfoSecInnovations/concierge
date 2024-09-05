import json
import requests
import os

HOST = os.getenv("OLLAMA_HOST") or "localhost"


def create_embeddings(text):
    data = {"model": "all-minilm", "prompt": text, "stream": False}
    response = requests.post(
        f"http://{HOST}:11434/api/embeddings", data=json.dumps(data)
    )
    return json.loads(response.text)["embedding"]


def load_model(model_name):
    # TODO several revs in the future... allow users to pick model.
    # very much low priority atm
    def is_loaded():
        models = requests.get(f"http://{HOST}:11434/api/tags")
        model_list = json.loads(models.text)["models"]
        return next(
            filter(lambda x: x["name"].split(":")[0] == model_name, model_list), None
        )

    while not is_loaded():
        print(f"{model_name} model not found. Please wait while it loads.")
        request = requests.post(
            f"http://{HOST}:11434/api/pull",
            data=json.dumps({"name": model_name}),
            stream=True,
        )
        current = 0
        for item in request.iter_lines():
            if item:
                value = json.loads(item)
                # TODO: display statuses
                if "total" in value:
                    if "completed" in value:
                        current = value["completed"]
                    yield (current, value["total"])
