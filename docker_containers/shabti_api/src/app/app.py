from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shabti_util import auth_enabled
from . import insecure_routes
from . import secure_routes
import os
from ..load_dotenv import load_env
from keycloak import KeycloakPostError, KeycloakAuthenticationError
import json
from shabti_types import (
    ShabtiError,
)
import logging


def create_app():
    load_env()

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

    # without security the API routes are simplified

    if not auth_enabled():
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
