from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from concierge_util import auth_enabled
from . import insecure_routes
from . import secure_routes
import os
from load_dotenv import load_env
from keycloak import KeycloakPostError
import json
from concierge_types import (
    CollectionExistsError,
    InvalidLocationError,
    InvalidUserError,
)

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
    def keycloak_authentication_error_handler(request: Request, exc: KeycloakPostError):
        return JSONResponse(
            content=json.loads(exc.response_body), status_code=exc.response_code
        )

    app.include_router(secure_routes.router)


@app.get("/")
def is_online():
    return Response("Shabti API is up and running!")


@app.exception_handler(CollectionExistsError)
def collection_exists_error_handler(request: Request, exc: CollectionExistsError):
    return JSONResponse(
        content={"error_type": "CollectionExistsError", "error_message": exc.message},
        status_code=500,
    )


@app.exception_handler(InvalidLocationError)
def invalid_location_error_handler(request: Request, exc: InvalidLocationError):
    return JSONResponse(
        content={
            "error_type": "InvalidLocationError",
            "error_message": 'location must be "private" or "shared"',
        },
        status_code=500,
    )


@app.exception_handler(InvalidUserError)
def invalid_user_error_handler(request: Request, exc: InvalidUserError):
    return JSONResponse(
        content={"error_type": "InvalidUserError", "error_message": exc.message},
        status_code=500,
    )
