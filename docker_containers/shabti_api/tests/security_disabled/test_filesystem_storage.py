import aiofiles
import aiofiles.os
import os
from ...src.app.opensearch import get_document_file_path
from ...src.app.document_collections import (
    delete_document,
    get_documents,
    delete_collection,
)

filename = "test_doc.txt"
file_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
file_path = os.path.join(file_dir, filename)


async def test_file_creation(shabti_client, shabti_collection_id):
    response = shabti_client.post(
        f"/collections/{shabti_collection_id}/documents/files",
        files=[("files", open(file_path, "rb"))],
    )
    doc_id = response.json()["document_id"]
    document_file_path = get_document_file_path(shabti_collection_id, doc_id)
    async with aiofiles.open(
        os.path.join(os.getenv("SHABTI_FILES_DIR"), document_file_path)
    ) as f:
        assert await f.read() == "This is not a real document, it's just a test."


async def test_file_deletion_with_document(shabti_collection_id, shabti_document_id):
    document_file_path = get_document_file_path(
        shabti_collection_id, shabti_document_id
    )
    await delete_document(None, shabti_collection_id, shabti_document_id)
    assert not await aiofiles.os.path.exists(
        os.path.join(os.getenv("SHABTI_FILES_DIR"), document_file_path)
    )


async def test_file_deletion_with_collection(shabti_client, shabti_collection_id):
    files = await aiofiles.os.listdir(file_dir)
    for file in files:
        shabti_client.post(
            f"/collections/{shabti_collection_id}/documents/files",
            files=[("files", open(os.path.join(file_dir, file), "rb"))],
        )
    docs = await get_documents(None, shabti_collection_id)
    paths = [
        get_document_file_path(shabti_collection_id, doc.document_id)
        for doc in docs.documents
    ]
    await delete_collection(None, shabti_collection_id)
    for path in paths:
        assert not await aiofiles.os.path.exists(
            os.path.join(os.getenv("SHABTI_FILES_DIR"), path)
        )
