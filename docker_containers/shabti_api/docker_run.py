import uvicorn
from src.app.app import app
from shabti_util import auth_enabled
from logging_config import logging_config
import os

args = {"app": app, "port": 15131, "host": "0.0.0.0"}

if os.getenv("SHABTI_LOGGING_ENABLED") == "True":
    args["log_config"] = logging_config()

if auth_enabled():
    args["ssl_keyfile"] = "api_certs/key.pem"
    args["ssl_certfile"] = "api_certs/cert.pem"

uvicorn.run(**args)
