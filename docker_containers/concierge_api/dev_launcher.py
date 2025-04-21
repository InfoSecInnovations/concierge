import uvicorn
from app.app import app
from concierge_util import auth_enabled
from load_dotenv import load_env
import os

load_env()
port = int(os.getenv("API_PORT", "15131"))
host = "localhost"

if auth_enabled():
    uvicorn.run(
        app=app,
        port=port,
        host=host,
        ssl_keyfile=os.getenv("API_KEY"),
        ssl_certfile=os.getenv("API_CERT"),
    )
else:
    uvicorn.run(app=app, port=port, host=host)
