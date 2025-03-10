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
from fastapi.responses import StreamingResponse
import aiofiles
from models import (
    BaseCollectionCreateInfo,
    CollectionInfo,
    DocumentInfo,
    DeletedDocumentInfo,
)

app = FastAPI()

# without security the API routes are simplified

if not auth_enabled():

    @app.post("/collections")
    async def create_collection_route(
        collection_info: BaseCollectionCreateInfo,
    ) -> CollectionInfo:
        return await create_collection(None, collection_info.collection_name)

    @app.get("/collections")
    async def get_collections_route() -> list[CollectionInfo]:
        return await get_collections(None)

    @app.delete("/collections/{collection_id}")
    async def delete_collection_route(collection_id: str) -> CollectionInfo:
        return await delete_collection(None, collection_id)

    @app.get("/collections/{collection_id}/documents")
    async def get_documents_route(collection_id: str) -> list[DocumentInfo]:
        return await get_documents(None, collection_id)

    @app.post("/collections/{collection_id}/documents/files")
    async def insert_files_document_route(collection_id: str, files: list[UploadFile]):
        paths = {}
        for file in files:
            async with aiofiles.tempfile.NamedTemporaryFile(
                suffix=file.filename, delete=False
            ) as fp:
                binary = await file.read()
                await fp.write(binary)
                paths[file.filename] = {"path": fp.name, "binary": binary}

        async def response_json():
            for filename, data in paths.items():
                doc = load_file(data["path"], filename)
                async for result in insert_document(
                    None, collection_id, doc, data["binary"]
                ):
                    yield result.model_dump_json(exclude_unset=True)

        return StreamingResponse(response_json())

    @app.post("/collections/{collection_id}/documents/urls")
    async def insert_url_document_route(collection_id: str, urls: list[str]):
        # TODO: loader
        return await insert_document(None, collection_id)

    @app.delete("/collections/{collection_id}/documents/{document_type}/{document_id}")
    async def delete_document_route(
        collection_id: str, document_type: str, document_id: str
    ) -> DeletedDocumentInfo:
        return await delete_document(None, collection_id, document_type, document_id)
