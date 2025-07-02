import uvicorn
from src.app.app import app
from shabti_util import auth_enabled
from logging_config import logging_config
import os

log_config = logging_config() if os.getenv("SHABTI_LOGGING_ENABLED") == "True" else None

if auth_enabled():
    uvicorn.run(
        app=app,
        port=15131,
        host="0.0.0.0",
        ssl_keyfile="api_certs/key.pem",
        ssl_certfile="api_certs/cert.pem",
        log_config=log_config,
    )
else:
    uvicorn.run(app=app, port=15131, host="0.0.0.0", log_config=log_config)
