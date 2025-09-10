from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import aiofiles
from shabti_types import PromptInfo, PromptChunk, PromptSource, DocumentInfo, PageInfo
from .prompting import stream_response, get_context
from .opensearch import get_temp_file
from .load_prompter_config import load_prompter_config
import json
from .shabti_logging import log_action, log_user_action, logging_enabled
from shabti_util import auth_enabled
from .document_collections import get_collection_info


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

        # TODO: log the no sources response

        return StreamingResponse(no_sources_response())

    async def stream_context_and_response():
        response = ""
        for source in context["sources"]:
            yield f"{PromptChunk(source=PromptSource(
                document_metadata=DocumentInfo(**source["doc_metadata"]),
                page_metadata=PageInfo(**source["page_metadata"])
            )).model_dump_json(exclude_unset=True)}\n"
        async for x in stream_response(
            context=context["context"],
            task_prompt=task_prompt,
            user_input=prompt_info.user_input,
            persona_prompt=persona_prompt,
            source_file_contents=source_file_contents,
        ):
            obj = json.loads(x)
            if "response" in obj:
                yield x
                if logging_enabled():
                    response += obj["response"]

        if logging_enabled():
            prompt = {
                "response": response,
                "sources": context["sources"],
                "input": prompt_info.user_input,
                "task": prompt_info.task,
            }
            if prompt_info.persona:
                prompt["persona"] = prompt_info.persona
            if prompt_info.enhancers:
                prompt["enhancers"] = prompt_info.enhancers
            if prompt_info.file_id:
                prompt["input_file"] = {
                    "file_id": prompt_info.file_id,
                    "contents": source_file_contents,
                }
            if auth_enabled():
                await log_user_action(
                    token,
                    "QUERY",
                    f"User ran a prompt on collection with ID {prompt_info.collection_id}",
                    collection=(
                        await get_collection_info(prompt_info.collection_id)
                    ).model_dump(),
                    prompt=prompt,
                )
            else:
                await log_action(
                    "QUERY",
                    f"User ran a prompt on collection with ID {prompt_info.collection_id}",
                    collection=(
                        await get_collection_info(prompt_info.collection_id)
                    ).model_dump(),
                    prompt=prompt,
                )

    return StreamingResponse(stream_context_and_response())
