import uvicorn
from src.app.app import app
from shabti_util import auth_enabled

if auth_enabled():
    uvicorn.run(
        app=app,
        port=15131,
        host="0.0.0.0",
        ssl_keyfile="api_certs/key.pem",
        ssl_certfile="api_certs/cert.pem",
    )
else:
    uvicorn.run(app=app, port=15131, host="0.0.0.0")
