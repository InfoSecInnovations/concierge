from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import aiofiles
from .models import (
    PromptInfo,
)
from .prompting import stream_response, get_context
from .opensearch import get_temp_file
from .load_prompter_config import load_prompter_config
import json


async def run_prompt(token: None | str, prompt_info: PromptInfo) -> StreamingResponse:
    tasks = load_prompter_config("tasks")
    if prompt_info.task not in tasks:
        raise HTTPException(status_code=400, detail="Requested task not found")
    task_prompt = tasks[prompt_info.task]["prompt"]

    if prompt_info.persona:
        personas = load_prompter_config("personas")
        if prompt_info.persona not in personas:
            raise HTTPException(status_code=400, detail="Requested persona not found")
        persona_prompt = personas[prompt_info.persona]["prompt"]

    else:
        persona_prompt = None

    if prompt_info.enhancers:
        enhancers = load_prompter_config("enhancers")
        enhancer_prompts = []
        for enhancer in prompt_info.enhancers:
            if enhancer not in enhancers:
                raise HTTPException(
                    status_code=400, detail="Requested enhancer not found"
                )
            enhancer_prompts.append(enhancers[enhancer]["prompt"])
    else:
        enhancer_prompts = None

    if prompt_info.file_id:
        file_path = get_temp_file(prompt_info.file_id)
        async with aiofiles.open(file_path) as f:
            source_file_contents = await f.read()
    else:
        source_file_contents = None

    context = await get_context(
        token, prompt_info.collection_id, 5, prompt_info.user_input
    )

    if not len(context["sources"]):

        def no_sources_response():
            yield f"{json.dumps({'response': 'No sources were found matching your query. Please refine your request to closer match the data in the database or ingest more data.'})}\n"

        return StreamingResponse(no_sources_response())

    async def stream_context_and_response():
        for source in context["sources"]:
            yield f"{json.dumps({'source': source})}\n"
        async for x in stream_response(
            context=context["context"],
            task_prompt=task_prompt,
            user_input=prompt_info.user_input,
            persona_prompt=persona_prompt,
            source_file_contents=source_file_contents,
        ):
            yield x

    return StreamingResponse(stream_context_and_response())
