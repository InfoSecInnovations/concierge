import uvicorn
from src.app.app import app
from shabti_util import auth_enabled
from src.load_dotenv import load_env
import os
from logging_config import logging_config

load_env()
port = int(os.getenv("API_PORT", "15131"))
host = "localhost"
log_config = (
    logging_config() if os.getenv("SHABTI_BASE_SERVICE").endswith("logging") else None
)

if auth_enabled():
    uvicorn.run(
        app=app,
        port=port,
        host=host,
        ssl_keyfile=os.getenv("API_KEY"),
        ssl_certfile=os.getenv("API_CERT"),
        log_config=log_config,
    )
else:
    uvicorn.run(app=app, port=port, host=host, log_config=log_config)
