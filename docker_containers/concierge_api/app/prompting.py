import json
import os
from .opensearch_prompting import get_context_from_opensearch
from .authorization import auth_enabled, authorize, UnauthorizedOperationError
from isi_util.async_single import asyncify
import httpx


def host():
    return os.getenv("OLLAMA_HOST") or "localhost"


async def get_context(token, collection_id: str, reference_limit: int, user_input: str):
    if auth_enabled():
        authorized = await authorize(token, collection_id, "read")
        if not authorized:
            raise UnauthorizedOperationError()
    return await asyncify(
        get_context_from_opensearch, collection_id, reference_limit, user_input
    )


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


async def get_response(
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
    # Ollama doesn't like the data in JSON, we have to dump it to string
    async with httpx.AsyncClient(timeout=None) as httpx_client:
        response = await httpx_client.post(
            f"http://{host()}:11434/api/generate", data=json.dumps(data)
        )
    if response.status_code != 200:
        print(response.content)
        return f"ollama status: {response.status_code}"

    return json.loads(response.text)["response"]


async def stream_response(
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
    # Ollama doesn't like the data in JSON, we have to dump it to string
    async with httpx.AsyncClient(timeout=None) as httpx_client:
        async with httpx_client.stream(
            "POST", f"http://{host()}:11434/api/generate", data=json.dumps(data)
        ) as response:
            async for line in response.aiter_lines():
                yield f"{line}\n"
