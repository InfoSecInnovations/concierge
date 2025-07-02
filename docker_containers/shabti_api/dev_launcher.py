import uvicorn
from src.app.app import app
from shabti_util import auth_enabled
from src.load_dotenv import load_env
import os
from logging_config import logging_config

load_env()
port = int(os.getenv("API_PORT", "15131"))
host = "localhost"
logging_enabled = os.getenv("SHABTI_BASE_SERVICE").endswith("logging")
log_config = logging_config() if logging_enabled else None
if logging_enabled:
    os.environ["SHABTI_LOGGING_ENABLED"] = "True"

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
