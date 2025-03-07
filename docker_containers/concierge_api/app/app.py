from fastapi import FastAPI, UploadFile
from document_collections import (
    create_collection,
    get_collections,
    delete_collection,
    get_documents,
    delete_document,
)
from ingesting import insert_document
from authorization import auth_enabled
from loading import load_file
import tempfile

app = FastAPI()

# without security the API routes are simplified

if not auth_enabled():

    @app.post("/collections")
    async def create_collection_route(name: str):
        return await create_collection(None, name)

    @app.get("/collections")
    async def get_collections_route():
        return await get_collections(None)

    @app.delete("/collections/{collection_id}")
    async def delete_collection_route(collection_id: str):
        return await delete_collection(None, collection_id)

    @app.get("/collections/{collection_id}/documents")
    async def get_documents_route(collection_id: str):
        return await get_documents(None, collection_id)

    @app.post("/collections/{collection_id}/documents/files")
    async def insert_files_document_route(collection_id: str, files: list[UploadFile]):
        for file in files:
            with tempfile.NamedTemporaryFile(suffix=file.filename, delete=False) as fp:
                fp.write(file.file.read())
                file_path = fp.name
            doc = load_file(file_path)
            async for result in insert_document(None, collection_id, doc):
                pass

    @app.post("/collections/{collection_id}/documents/urls")
    async def insert_url_document_route(collection_id: str, urls: list[str]):
        # TODO: loader
        return await insert_document(None, collection_id)

    @app.delete("/collections/{collection_id}/documents/{document_type}/{document_id}")
    async def delete_document_route(
        collection_id: str, document_type: str, document_id: str
    ):
        return await delete_document(None, collection_id, document_type, document_id)
