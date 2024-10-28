import json
import requests
import os

HOST = os.getenv("OLLAMA_HOST", "localhost")


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


def create_embeddings_ollama(text):
    data = {"model": "all-minilm", "input": text, "stream": False}
    response = requests.post(
        f"http://{HOST}:11434/api/embed", data=json.dumps(data)
    ).json()
    # if there was an error in the response, it may be because the model wasn't present
    # TODO: check the type of error
    if "error" in response:
        for _ in load_model("all-minilm"):
            # TODO: something
            pass
        response = requests.post(
            f"http://{HOST}:11434/api/embed", data=json.dumps(data)
        ).json()
        # if at this point it still didn't work we'll let it raise the exception
    return response["embeddings"]
