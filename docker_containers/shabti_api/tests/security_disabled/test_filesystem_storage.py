import aiofiles
import os
from ...src.app.opensearch import get_document_file_path

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


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
