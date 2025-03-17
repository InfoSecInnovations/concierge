from fastapi import APIRouter
from fastapi import UploadFile, HTTPException
from document_collections import (
    create_collection,
    get_collections,
    delete_collection,
    get_documents,
    delete_document,
)
from ingesting import insert_document
from loading import load_file
from fastapi.responses import StreamingResponse
import aiofiles
from models import (
    BaseCollectionCreateInfo,
    CollectionInfo,
    DocumentInfo,
    DeletedDocumentInfo,
    ServiceStatus,
    PromptInfo,
    TaskInfo,
    PromptConfigInfo,
    TempFileInfo,
)
from loaders.web import WebLoader
from status import check_ollama, check_opensearch
from prompting import stream_response, get_context
from opensearch import set_temp_file, get_temp_file
from load_prompter_config import load_prompter_config

router = APIRouter()


@router.post("/collections", response_model_exclude_unset=True)
async def create_collection_route(
    collection_info: BaseCollectionCreateInfo,
) -> CollectionInfo:
    return await create_collection(None, collection_info.collection_name)


@router.get("/collections", response_model_exclude_unset=True)
async def get_collections_route() -> list[CollectionInfo]:
    return await get_collections(None)


@router.delete("/collections/{collection_id}", response_model_exclude_unset=True)
async def delete_collection_route(collection_id: str) -> CollectionInfo:
    return await delete_collection(None, collection_id)


@router.get("/collections/{collection_id}/documents", response_model_exclude_unset=True)
async def get_documents_route(collection_id: str) -> list[DocumentInfo]:
    return await get_documents(None, collection_id)


@router.post(
    "/collections/{collection_id}/documents/files", response_model_exclude_unset=True
)
async def insert_files_document_route(
    collection_id: str, files: list[UploadFile]
) -> StreamingResponse:
    paths = {}
    for file in files:
        async with aiofiles.tempfile.NamedTemporaryFile(
            suffix=file.filename, delete=False
        ) as fp:
            binary = await file.read()
            await fp.write(binary)
            paths[file.filename] = {"path": fp.name, "binary": binary}

    async def response_json():
        for filename, data in paths.items():
            doc = load_file(data["path"], filename)
            if doc:
                async for result in insert_document(
                    None, collection_id, doc, data["binary"]
                ):
                    yield result.model_dump_json(exclude_unset=True)

    return StreamingResponse(response_json())


@router.post(
    "/collections/{collection_id}/documents/urls", response_model_exclude_unset=True
)
async def insert_urls_document_route(
    collection_id: str, urls: list[str]
) -> StreamingResponse:
    async def response_json():
        for url in urls:
            doc = WebLoader.load(url)
            if doc:
                async for result in insert_document(None, collection_id, doc):
                    yield result.model_dump_json(exclude_unset=True)

    return StreamingResponse(response_json())


@router.delete(
    "/collections/{collection_id}/documents/{document_type}/{document_id}",
    response_model_exclude_unset=True,
)
async def delete_document_route(
    collection_id: str, document_type: str, document_id: str
) -> DeletedDocumentInfo:
    return await delete_document(None, collection_id, document_type, document_id)


@router.get("/tasks", response_model_exclude_unset=True)
def get_tasks_route() -> dict[str, TaskInfo]:
    tasks = load_prompter_config("tasks")
    return {key: TaskInfo(**value) for key, value in tasks.items()}


@router.get("/personas")
def get_personas_route() -> dict[str, PromptConfigInfo]:
    personas = load_prompter_config("personas")
    return {key: PromptConfigInfo(**value) for key, value in personas.items()}


@router.get("/enhancers")
def get_enhancers_route() -> dict[str, PromptConfigInfo]:
    enhancers = load_prompter_config("enhancers")
    return {key: PromptConfigInfo(**value) for key, value in enhancers.items()}


@router.post("/prompt/source_file")
async def prompt_file_route(file: UploadFile) -> TempFileInfo:
    async with aiofiles.tempfile.NamedTemporaryFile(delete=False) as fp:
        binary = await file.read()
        await fp.write(binary)
        id = set_temp_file(fp.name)
    return TempFileInfo(id=id)


@router.post("/prompt")
async def prompt_route(prompt_info: PromptInfo) -> StreamingResponse:
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
            enhancer_prompts.routerend(enhancers[enhancer]["prompt"])
    else:
        enhancer_prompts = None

    if prompt_info.file_id:
        file_path = get_temp_file(prompt_info.file_id)
        async with aiofiles.open(file_path) as f:
            source_file_contents = await f.read()
    else:
        source_file_contents = None

    context = await get_context(
        None, prompt_info.collection_id, 5, prompt_info.user_input
    )

    return StreamingResponse(
        stream_response(
            context=context["context"],
            task_prompt=task_prompt,
            user_input=prompt_info.user_input,
            persona_prompt=persona_prompt,
            source_file_contents=source_file_contents,
        )
    )


@router.get("/status/ollama")
def ollama_status():
    return ServiceStatus(running=check_ollama())


@router.get("/status/opensearch")
def opensearch_status():
    return ServiceStatus(running=check_opensearch())
