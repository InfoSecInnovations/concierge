from fastapi import APIRouter
from fastapi import UploadFile
from .document_collections import (
    create_collection,
    get_collections,
    delete_collection,
    get_documents,
    delete_document,
)
from fastapi.responses import StreamingResponse
from .models import (
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
from .status import check_ollama, check_opensearch
from .load_prompter_config import load_prompter_config
from .insert_uploaded_files import insert_uploaded_files
from .insert_urls import insert_urls
from .run_prompt import run_prompt
from .upload_prompt_file import upload_prompt_file
from .opensearch_binary import serve_binary

router = APIRouter()


@router.post("/collections", response_model_exclude_unset=True, status_code=201)
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
    return await insert_uploaded_files(None, collection_id, files)


@router.post(
    "/collections/{collection_id}/documents/urls", response_model_exclude_unset=True
)
async def insert_urls_document_route(
    collection_id: str, urls: list[str]
) -> StreamingResponse:
    return insert_urls(None, collection_id, urls)


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
    return await upload_prompt_file(file)


@router.get("/prompt")
async def prompt_route(prompt_info: PromptInfo) -> StreamingResponse:
    return await run_prompt(None, prompt_info)


@router.get("/status/ollama")
def ollama_status():
    return ServiceStatus(running=check_ollama())


@router.get("/status/opensearch")
def opensearch_status():
    return ServiceStatus(running=check_opensearch())


@router.get("/files/{collection_id}/{doc_type}/{doc_id}")
async def get_files_route(collection_id: str, doc_type: str, doc_id: str):
    return await serve_binary(collection_id, doc_id, doc_type)
