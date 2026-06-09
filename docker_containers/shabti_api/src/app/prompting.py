import os
from .opensearch_prompting import get_context_from_opensearch
from .authorization import authorize, UnauthorizedOperationError
from isi_util.async_single import asyncify
import httpx
from shabti_util import auth_enabled
from httpx_sse import aconnect_sse
from .models import get_model_id


def host():
    return os.getenv("LLM_HOST") or "localhost"


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

    # TODO: pass model name in

    data = {
        "model": get_model_id("mistral7b"),
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=None) as httpx_client:
        async with aconnect_sse(
            httpx_client,
            "POST",
            f"http://{os.getenv('LLM_HOST')}:11434/v1/chat/completions",
            json=data,
        ) as event_source:
            async for sse in event_source.aiter_sse():
                yield f"{sse.data}\n"
