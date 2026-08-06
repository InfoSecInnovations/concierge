import os
from .opensearch_prompting import get_context_from_opensearch
from isi_util.async_single import asyncify
import httpx
from httpx_sse import aconnect_sse


def host():
    return os.getenv("LLM_HOST") or "localhost"


async def get_context(collection_id: str, reference_limit: int, user_input: str):
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
    model_name,
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

    data = {
        "model": model_name,
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
