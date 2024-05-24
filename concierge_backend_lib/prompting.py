import json
import requests
from sentence_transformers import SentenceTransformer


def load_model():
    # TODO several revs in the future... allow users to pick model.
    # very much low priority atm
    models = requests.get("http://localhost:11434/api/tags")
    model_list = json.loads(models.text)["models"]
    if not next(
        filter(lambda x: x["name"].split(":")[0] == "mistral", model_list), None
    ):
        print("mistral model not found. Please wait while it loads.")
        request = requests.post(
            "http://localhost:11434/api/pull",
            data=json.dumps({"name": "mistral"}),
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


stransform = SentenceTransformer("paraphrase-MiniLM-L6-v2")
search_params = {
    "metric_type": "COSINE",
    "params": {
        "radius": 0.5
    },  # -1.0 to 1.0, positive values indicate similarity, negative values indicate difference
}


def prepare_prompt(
    context,
    task_prompt,
    user_input,
    persona_prompt=None,
    enhancer_prompts=None,
    source_file_contents=None,
):
    prompt = task_prompt

    if persona_prompt:
        prompt = persona_prompt + "\n\n" + prompt

    if enhancer_prompts:
        for enhancer_prompt in enhancer_prompts:
            prompt = prompt + "\n\n" + enhancer_prompt

    prompt = prompt + "\n\nContext: " + context + "\n\nUser input: " + user_input

    if source_file_contents:
        prompt = prompt + "\n\nSource file: " + source_file_contents

    return prompt


def get_response(
    context,
    task_prompt,
    user_input,
    persona_prompt=None,
    enhancer_prompts=None,
    source_file_contents=None,
):
    prompt = prepare_prompt(
        context,
        task_prompt,
        user_input,
        persona_prompt,
        enhancer_prompts,
        source_file_contents,
    )

    data = {"model": "mistral", "prompt": prompt, "stream": False}

    response = requests.post(
        "http://127.0.0.1:11434/api/generate", data=json.dumps(data)
    )

    print(f"Response: {response}")

    if response.status_code != 200:
        return f"ollama status: {response.status_code}"

    return json.loads(response.text)["response"]


def stream_response(
    context,
    task_prompt,
    user_input,
    persona_prompt=None,
    enhancer_prompts=None,
    source_file_contents=None,
):
    prompt = prepare_prompt(
        context,
        task_prompt,
        user_input,
        persona_prompt,
        enhancer_prompts,
        source_file_contents,
    )

    data = {"model": "mistral", "prompt": prompt, "stream": True}

    response = requests.post(
        "http://127.0.0.1:11434/api/generate", data=json.dumps(data)
    )

    for item in response.iter_lines():
        if item:
            value = json.loads(item)
            if "response" in value:
                yield value["response"]
