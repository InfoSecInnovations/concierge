import json
import requests
import os
from dotenv import load_dotenv
from .opensearch_prompting import get_context_from_opensearch
from .authorization import auth_enabled, authorize, UnauthorizedOperationError

load_dotenv()
HOST = os.getenv("OLLAMA_HOST") or "localhost"


def get_context(token, collection_id: str, reference_limit: int, user_input: str):
    if auth_enabled:
        authorized = authorize(token, collection_id, "read")
        if not authorized:
            raise UnauthorizedOperationError()
    return get_context_from_opensearch(collection_id, reference_limit, user_input)


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

    response = requests.post(f"http://{HOST}:11434/api/generate", data=json.dumps(data))

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

    response = requests.post(f"http://{HOST}:11434/api/generate", data=json.dumps(data))

    for item in response.iter_lines():
        if item:
            value = json.loads(item)
            if "response" in value:
                yield value["response"]
