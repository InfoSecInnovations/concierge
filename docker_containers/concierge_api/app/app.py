from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from authorization import auth_enabled
import insecure_routes
import secure_routes
from load_dotenv import load_env

load_env()

app = FastAPI()

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
    app.include_router(secure_routes.router)
