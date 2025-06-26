import uvicorn
from src.app.app import app
from shabti_util import auth_enabled
from src.load_dotenv import load_env
import os
from importlib.resources import files

load_env()
port = int(os.getenv("API_PORT", "15131"))
host = "localhost"
logging_config_file = os.path.join(files(), "logging_config.yml")

if auth_enabled():
    uvicorn.run(
        app=app,
        port=port,
        host=host,
        ssl_keyfile=os.getenv("API_KEY"),
        ssl_certfile=os.getenv("API_CERT"),
        log_config=logging_config_file,
    )
else:
    uvicorn.run(app=app, port=port, host=host)
