from fastapi import APIRouter, Depends, UploadFile, HTTPException
from .document_collections import (
    get_collections,
    create_collection,
    delete_collection,
    delete_document,
    get_document_types,
)
from fastapi.security import OAuth2AuthorizationCodeBearer
from typing import Annotated
from shabti_keycloak import server_url, get_token_info, get_keycloak_client
from shabti_types import (
    AuthzCollectionCreateInfo,
    AuthzCollectionInfo,
    DeletedDocumentInfo,
    ServiceStatus,
    PromptInfo,
    TaskInfo,
    PromptConfigInfo,
    TempFileInfo,
    ModelInfo,
    ModelLoadInfo,
    DocumentIngestInfo,
    DocumentIngestError,
    PromptChunk,
)
from .insert_uploaded_files import insert_uploaded_files
from .insert_urls import insert_urls
from jwcrypto.jwt import JWTExpired
from .status import check_llm, check_opensearch
from .run_prompt import run_prompt
from .load_prompter_config import load_prompter_config
from .upload_prompt_file import upload_prompt_file
from .opensearch_binary import serve_binary
from .authorization import (
    authorize,
    list_permissions,
    has_scope,
    list_scopes,
    UnauthorizedOperationError,
)
from .models import load_model
from collections.abc import AsyncIterable
import asyncio

oauth_2_scheme = OAuth2AuthorizationCodeBearer(
    tokenUrl=f"{server_url()}/realms/shabti/protocol/openid-connect/token",
    authorizationUrl=f"{server_url()}/realms/shabti/protocol/openid-connect/auth",
    refreshUrl=f"{server_url()}/realms/shabti/protocol/openid-connect/token",
)


async def valid_access_token(access_token: Annotated[str, Depends(oauth_2_scheme)]):
    try:
        client = get_keycloak_client()
        client.decode_token(access_token)
        return access_token
    except JWTExpired:
        raise HTTPException(status_code=401, detail="Token expired")


class AuthChecker:
    def __init__(self, scope: str = "read"):
        self.scope = scope

    async def __call__(
        self,
        credentials: Annotated[str, Depends(valid_access_token)],
        collection_id: str,
    ):
        authorized = await authorize(credentials, collection_id, self.scope)
        if not authorized:
            raise UnauthorizedOperationError()


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
        credentials,
        collection_info.collection_name,
        collection_info.location,
        collection_info.owner_username,
    )


@router.delete("/collections/{collection_id}", response_model_exclude_unset=True)
async def delete_collection_route(
    collection_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> AuthzCollectionInfo:
    return await delete_collection(credentials, collection_id)


@router.get(
    "/collections/{collection_id}/document_types", response_model_exclude_unset=True
)
async def get_document_types_route(
    collection_id: str, credentials: Annotated[str, Depends(valid_access_token)]
) -> list[str]:
    return await get_document_types(credentials, collection_id)


@router.post(
    "/collections/{collection_id}/documents/files",
    response_model_exclude_unset=True,
    dependencies=[Depends(AuthChecker("update"))],
)
async def insert_files_document_route(
    collection_id: str,
    files: list[UploadFile],
    credentials: Annotated[str, Depends(valid_access_token)],
) -> AsyncIterable[DocumentIngestInfo | DocumentIngestError]:
    async for x in insert_uploaded_files(credentials, collection_id, files):
        yield x


@router.post(
    "/collections/{collection_id}/documents/urls",
    response_model_exclude_unset=True,
    dependencies=[Depends(AuthChecker("update"))],
)
async def insert_urls_document_route(
    collection_id: str,
    urls: list[str],
    credentials: Annotated[str, Depends(valid_access_token)],
) -> AsyncIterable[DocumentIngestInfo]:
    async for x in insert_urls(credentials, collection_id, urls):
        yield x


@router.delete(
    "/collections/{collection_id}/documents/{document_id}",
    response_model_exclude_unset=True,
)
async def delete_document_route(
    collection_id: str,
    document_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> DeletedDocumentInfo:
    return await delete_document(credentials, collection_id, document_id)


@router.get("/collections/{collection_id}/scopes")
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


class PromptBodyAuthChecker:
    def __init__(self, scope: str = "read"):
        self.scope = scope

    async def __call__(
        self,
        prompt_info: PromptInfo,
        credentials: Annotated[str, Depends(valid_access_token)],
    ):
        authorized = await authorize(credentials, prompt_info.collection_id, self.scope)
        if not authorized:
            raise UnauthorizedOperationError()


@router.post("/prompt", dependencies=[Depends(PromptBodyAuthChecker("read"))])
async def prompt_route(
    prompt_info: PromptInfo, credentials: Annotated[str, Depends(valid_access_token)]
) -> AsyncIterable[PromptChunk]:
    async for x in run_prompt(credentials, prompt_info):
        yield x


@router.get("/status/llm")
def llm_status():
    return ServiceStatus(running=check_llm())


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


@router.get("/files/{collection_id}/{doc_id}")
async def get_files_route(
    collection_id: str,
    doc_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
):
    authorized = await authorize(credentials, collection_id, "read")
    if not authorized:
        raise UnauthorizedOperationError()
    return await serve_binary(collection_id, doc_id)


@router.post("/models/pull")
async def load_model_route(model_info: ModelInfo) -> AsyncIterable[ModelLoadInfo]:
    # TODO: should this be locked behind higher permissions levels?
    async for x in load_model(model_info.model_name):
        yield x
