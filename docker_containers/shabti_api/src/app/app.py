from fastapi import FastAPI, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shabti_util import auth_enabled
from .routers import insecure_routes
from .routers import secure_routes
import os
from keycloak import KeycloakPostError, KeycloakAuthenticationError
import json
from shabti_types import ShabtiError, DocumentList
import logging
from fastapi import Depends
from typing import Annotated
from .functionality.document_collections import get_documents
from .dependencies.valid_access_token import valid_access_token
from fastapi import UploadFile
from .functionality.document_collections import (
    delete_document,
    get_document_types,
)
from shabti_types import (
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
from .functionality.insert_uploaded_files import insert_uploaded_files
from .functionality.insert_urls import insert_urls
from .functionality.status import check_llm, check_opensearch
from .functionality.run_prompt import run_prompt
from .functionality.load_prompter_config import load_prompter_config
from .functionality.upload_prompt_file import upload_prompt_file
from .functionality.opensearch_binary import serve_binary
from .authorization import (
    authorize,
    list_scopes,
    UnauthorizedOperationError,
)
from .functionality.models import load_model
from collections.abc import AsyncIterable
from .dependencies.auth_checker import AuthChecker
from .dependencies.no_auth import NoAuth


def create_app():
    auth_is_enabled = auth_enabled()

    def none_access_token():
        return None

    # if security is disabled we will just use None as the value of the token, which is supported by the underlying functions
    # this allows us to avoid duplicating all the routes
    access_token = valid_access_token if auth_is_enabled else none_access_token

    auth_class = AuthChecker if auth_is_enabled else NoAuth

    app = FastAPI(
        swagger_ui_init_oauth={
            "clientId": os.getenv("KEYCLOAK_CLIENT_ID"),
            "clientSecret": os.getenv("KEYCLOAK_CLIENT_SECRET"),
        }
    )

    # TODO: probably don't wildcard this
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # there are still a few routes which are specific to security being enabled or not
    if not auth_is_enabled:
        app.include_router(insecure_routes.router)
    else:

        @app.exception_handler(KeycloakPostError)
        def keycloak_post_error_handler(request: Request, exc: KeycloakPostError):
            return JSONResponse(
                content=json.loads(exc.response_body), status_code=exc.response_code
            )

        @app.exception_handler(KeycloakAuthenticationError)
        def keycloak_authentication_error_handler(
            request: Request, exc: KeycloakAuthenticationError
        ):
            return JSONResponse(
                content=json.loads(exc.response_body), status_code=exc.response_code
            )

        app.include_router(secure_routes.router)

    @app.get("/")
    def is_online():
        return Response("Shabti API is up and running!")

    @app.get(
        "/collections/{collection_id}/documents", response_model_exclude_unset=True
    )
    async def get_documents_route(
        collection_id: str,
        credentials: Annotated[str | None, Depends(access_token)],
        search: str | None = None,
        sort: str | None = None,
        max_results: int | None = None,
        filter_document_type: Annotated[list[str] | None, Query()] = None,
        page: int = 0,
    ) -> DocumentList:
        return await get_documents(
            credentials,
            collection_id,
            search,
            sort,
            max_results,
            filter_document_type,
            page,
        )

    @app.get(
        "/collections/{collection_id}/document_types", response_model_exclude_unset=True
    )
    async def get_document_types_route(
        collection_id: str, credentials: Annotated[str, Depends(access_token)]
    ) -> list[str]:
        return await get_document_types(credentials, collection_id)

    @app.post(
        "/collections/{collection_id}/documents/files",
        response_model_exclude_unset=True,
        dependencies=[Depends(auth_class("update"))],
    )
    async def insert_files_document_route(
        collection_id: str,
        files: list[UploadFile],
        credentials: Annotated[str, Depends(access_token)],
    ) -> AsyncIterable[DocumentIngestInfo | DocumentIngestError]:
        async for x in insert_uploaded_files(credentials, collection_id, files):
            yield x

    @app.post(
        "/collections/{collection_id}/documents/urls",
        response_model_exclude_unset=True,
        dependencies=[Depends(auth_class("update"))],
    )
    async def insert_urls_document_route(
        collection_id: str,
        urls: list[str],
        credentials: Annotated[str, Depends(access_token)],
    ) -> AsyncIterable[DocumentIngestInfo]:
        async for x in insert_urls(credentials, collection_id, urls):
            yield x

    @app.delete(
        "/collections/{collection_id}/documents/{document_id}",
        response_model_exclude_unset=True,
    )
    async def delete_document_route(
        collection_id: str,
        document_id: str,
        credentials: Annotated[str, Depends(access_token)],
    ) -> DeletedDocumentInfo:
        return await delete_document(credentials, collection_id, document_id)

    @app.get("/collections/{collection_id}/scopes")
    async def get_collection_scopes(
        collection_id: str, credentials: Annotated[str, Depends(access_token)]
    ):
        return await list_scopes(credentials, collection_id)

    @app.get(
        "/tasks",
        response_model_exclude_unset=True,
        dependencies=[Depends(access_token)],
    )
    def get_tasks_route() -> dict[str, TaskInfo]:
        tasks = load_prompter_config("tasks")
        return {key: TaskInfo(**value) for key, value in tasks.items()}

    @app.get("/personas", dependencies=[Depends(access_token)])
    def get_personas_route() -> dict[str, PromptConfigInfo]:
        personas = load_prompter_config("personas")
        return {key: PromptConfigInfo(**value) for key, value in personas.items()}

    @app.get("/enhancers", dependencies=[Depends(access_token)])
    def get_enhancers_route() -> dict[str, PromptConfigInfo]:
        enhancers = load_prompter_config("enhancers")
        return {key: PromptConfigInfo(**value) for key, value in enhancers.items()}

    @app.post("/prompt/source_file", dependencies=[Depends(access_token)])
    async def prompt_file_route(file: UploadFile) -> TempFileInfo:
        # TODO: should there be more restrictions on this route to avoid spamming the server with files?
        # TODO: maybe something like S3 upload where we pregenerate the URL or ID so a file can only be linked to a prompt?
        return await upload_prompt_file(file)

    class PromptBodyAuthChecker:
        def __init__(self, scope: str = "read"):
            self.scope = scope

        async def __call__(
            self,
            prompt_info: PromptInfo,
            credentials: Annotated[str, Depends(access_token)],
        ):
            authorized = await authorize(
                credentials, prompt_info.collection_id, self.scope
            )
            if not authorized:
                raise UnauthorizedOperationError()

    body_checker = PromptBodyAuthChecker if auth_is_enabled else NoAuth

    @app.post("/prompt", dependencies=[Depends(body_checker("read"))])
    async def prompt_route(
        prompt_info: PromptInfo, credentials: Annotated[str, Depends(access_token)]
    ) -> AsyncIterable[PromptChunk]:
        async for x in run_prompt(credentials, prompt_info):
            yield x

    @app.get("/status/llm")
    def llm_status():
        return ServiceStatus(running=check_llm())

    @app.get("/status/opensearch")
    def opensearch_status():
        return ServiceStatus(running=check_opensearch())

    @app.get(
        "/files/{collection_id}/{doc_id}", dependencies=[Depends(auth_class("read"))]
    )
    async def get_files_route(
        collection_id: str,
        doc_id: str,
        credentials: Annotated[str, Depends(access_token)],
    ):
        return await serve_binary(collection_id, doc_id)

    @app.post("/models/pull", dependencies=[Depends(access_token)])
    async def load_model_route(model_info: ModelInfo) -> AsyncIterable[ModelLoadInfo]:
        # TODO: should this be locked behind higher permissions levels?
        async for x in load_model(model_info.model_name):
            yield x

    @app.exception_handler(ShabtiError)
    def shabti_error_handler(request: Request, exc: ShabtiError):
        logger = logging.getLogger("shabti")
        logger.info(
            exc.message,
            extra={
                "action": "HTTP ERROR",
                "error_type": exc.__class__.__name__,
                **{key: value for key, value in vars(exc).items() if key != "message"},
            },
        )
        return JSONResponse(
            content={
                "error_type": exc.__class__.__name__,
                **vars(exc),
            },
            status_code=exc.status,
        )

    return app


app = create_app()
