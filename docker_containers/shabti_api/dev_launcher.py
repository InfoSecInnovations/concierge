import uvicorn
from src.app.app import app
from shabti_util import auth_enabled
from src.load_dotenv import load_env
import os
from logging_config import logging_config

load_env()

args = {"app": app, "port": int(os.getenv("API_PORT", "15131")), "host": "localhost"}

if os.getenv("SHABTI_BASE_SERVICE", "").endswith("logging"):
    args["log_config"] = logging_config()

if auth_enabled():
    args["ssl_keyfile"] = os.getenv("API_KEY")
    args["ssl_certfile"] = os.getenv("API_CERT")

uvicorn.run(**args)
