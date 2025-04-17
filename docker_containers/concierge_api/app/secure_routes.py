from fastapi import APIRouter, Depends, UploadFile, HTTPException
from .document_collections import (
    get_collections,
    create_collection,
    delete_collection,
    get_documents,
    delete_document,
)
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import StreamingResponse
from typing import Annotated
from concierge_keycloak import server_url, get_token_info, get_keycloak_client
from concierge_types import (
    AuthzCollectionCreateInfo,
    AuthzCollectionInfo,
    DocumentInfo,
    DeletedDocumentInfo,
    ServiceStatus,
    PromptInfo,
    TaskInfo,
    PromptConfigInfo,
    TempFileInfo,
    CollectionInfo,
    ModelInfo,
)
from .insert_uploaded_files import insert_uploaded_files
from .insert_urls import insert_urls
from jwcrypto.jwt import JWTExpired
from .status import check_ollama, check_opensearch
from .run_prompt import run_prompt
from .load_prompter_config import load_prompter_config
from .upload_prompt_file import upload_prompt_file
from .opensearch_binary import serve_binary
from .authorization import authorize, list_permissions, has_scope, list_scopes
from .ollama import load_model
import asyncio

oauth_2_scheme = OAuth2AuthorizationCodeBearer(
    tokenUrl=f"{server_url()}/realms/concierge/protocol/openid-connect/token",
    authorizationUrl=f"{server_url()}/realms/concierge/protocol/openid-connect/auth",
    refreshUrl=f"{server_url()}/realms/concierge/protocol/openid-connect/token",
)


async def valid_access_token(access_token: Annotated[str, Depends(oauth_2_scheme)]):
    try:
        client = get_keycloak_client()
        client.decode_token(access_token)
        return access_token
    except JWTExpired:
        raise HTTPException(status_code=401, detail="Token expired")


# all these routes require a valid account to view
router = APIRouter(dependencies=[Depends(valid_access_token)])


@router.get("/collections", response_model_exclude_unset=True)
async def get_collections_route(
    credentials: Annotated[str, Depends(valid_access_token)],
) -> list[AuthzCollectionInfo]:
    return await get_collections(credentials)


@router.post("/collections", response_model_exclude_unset=True, status_code=201)
async def create_collection_route(
    collection_info: AuthzCollectionCreateInfo,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> AuthzCollectionInfo:
    return await create_collection(
        credentials, collection_info.collection_name, collection_info.location
    )


@router.delete("/collections/{collection_id}", response_model_exclude_unset=True)
async def delete_collection_route(
    collection_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> CollectionInfo:
    return await delete_collection(credentials, collection_id)


@router.get(
    "/collections/{collection_id}/documents",
    response_model_exclude_unset=True,
    response_model=list[DocumentInfo],
)
async def get_documents_route(
    collection_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> list[DocumentInfo]:
    return await get_documents(credentials, collection_id)


@router.post(
    "/collections/{collection_id}/documents/files", response_model_exclude_unset=True
)
async def insert_files_document_route(
    collection_id: str,
    files: list[UploadFile],
    credentials: Annotated[str, Depends(valid_access_token)],
) -> StreamingResponse:
    return await insert_uploaded_files(credentials, collection_id, files)


@router.post(
    "/collections/{collection_id}/documents/urls", response_model_exclude_unset=True
)
async def insert_urls_document_route(
    collection_id: str,
    urls: list[str],
    credentials: Annotated[str, Depends(valid_access_token)],
) -> StreamingResponse:
    return insert_urls(credentials, collection_id, urls)


@router.delete(
    "/collections/{collection_id}/documents/{document_type}/{document_id}",
    response_model_exclude_unset=True,
)
async def delete_document_route(
    collection_id: str,
    document_type: str,
    document_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> DeletedDocumentInfo:
    return await delete_document(credentials, collection_id, document_type, document_id)


@router.get("/{collection_id}/scopes")
async def get_collection_scopes(
    collection_id: str, credentials: Annotated[str, Depends(valid_access_token)]
):
    return await list_scopes(credentials, collection_id)


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
async def prompt_route(
    prompt_info: PromptInfo, credentials: Annotated[str, Depends(valid_access_token)]
) -> StreamingResponse:
    return await run_prompt(credentials, prompt_info)


@router.get("/status/ollama")
def ollama_status():
    return ServiceStatus(running=check_ollama())


@router.get("/status/opensearch")
def opensearch_status():
    return ServiceStatus(running=check_opensearch())


@router.get("/user_info")
async def get_user_info_route(credentials: Annotated[str, Depends(valid_access_token)]):
    return await get_token_info(credentials)


@router.get("/permissions")
async def get_permissions(credentials: Annotated[str, Depends(valid_access_token)]):
    permissions, read, update, delete = await asyncio.gather(
        list_permissions(credentials),
        has_scope(credentials, "read"),
        has_scope(credentials, "update"),
        has_scope(credentials, "delete"),
    )
    if read:
        permissions.add("read")
    if update:
        permissions.add("update")
    if delete:
        permissions.add("delete")
    return permissions


@router.get("/files/{collection_id}/{doc_type}/{doc_id}")
async def get_files_route(
    collection_id: str,
    doc_type: str,
    doc_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
):
    await authorize(credentials, collection_id, "read")
    return await serve_binary(collection_id, doc_id, doc_type)


@router.post("/models/pull")
async def load_model_route(model_info: ModelInfo):
    # TODO: should this be locked behind a higher permission level?
    return load_model(model_info.model_name)
