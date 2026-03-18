from ...src.app.opensearch import get_temp_file
import os
import aiofiles

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


async def test_source_file(shabti_client):
    response = shabti_client.post(
        "/prompt/source_file", files=[("file", open(file_path, "rb"))]
    )
    assert response.status_code == 200
    file_id = response.json()["id"]
    prompt_file_path = get_temp_file(file_id)
    assert prompt_file_path
    async with aiofiles.open(prompt_file_path) as f:
        assert await f.read() == "This is not a real document, it's just a test."
