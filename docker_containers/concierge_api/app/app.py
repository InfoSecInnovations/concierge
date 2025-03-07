from fastapi import FastAPI
from app.document_collections import create_collection, get_collections
from app.authorization import auth_enabled

app = FastAPI()

# without security the API routes are simplified

if not auth_enabled():

    @app.post("/collections")
    async def post_create_collection(name: str):
        return await create_collection(None, name)

    @app.get("/collections")
    async def list_collections():
        return await get_collections(None)
