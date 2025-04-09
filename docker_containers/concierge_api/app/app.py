from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from concierge_util import auth_enabled
from . import insecure_routes
from . import secure_routes
import os
from load_dotenv import load_env
from keycloak import KeycloakPostError
import json

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
