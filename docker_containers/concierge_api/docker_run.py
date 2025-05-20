import uvicorn
from app.app import app
from concierge_util import auth_enabled
from sentence_transformers import SentenceTransformer

print(
    "initializing embeddings model (if this is the first run, it can take some time)..."
)
SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

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
