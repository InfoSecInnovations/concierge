from fastapi import FastAPI, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shabti_util import auth_enabled
from . import insecure_routes
from . import secure_routes
import os
from keycloak import KeycloakPostError, KeycloakAuthenticationError
import json
from shabti_types import ShabtiError, DocumentList
import logging
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from typing import Annotated
from shabti_keycloak import server_url, get_keycloak_client
from jwcrypto.jwt import JWTExpired
from .document_collections import get_documents


def create_app():
    auth_is_enabled = auth_enabled()

    oauth_2_scheme = OAuth2AuthorizationCodeBearer(
        tokenUrl=f"{server_url()}/realms/shabti/protocol/openid-connect/token",
        authorizationUrl=f"{server_url()}/realms/shabti/protocol/openid-connect/auth",
        refreshUrl=f"{server_url()}/realms/shabti/protocol/openid-connect/token",
    )

    async def valid_access_token(
        access_token: Annotated[str, Depends(oauth_2_scheme)],
    ):
        try:
            client = get_keycloak_client()
            client.decode_token(access_token)
            return access_token
        except JWTExpired:
            raise HTTPException(status_code=401, detail="Token expired")

    def no_access_token():
        return None

    access_token = valid_access_token if auth_is_enabled else no_access_token

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
