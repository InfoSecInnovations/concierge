from fastapi.testclient import TestClient
from app.app import app
from app.opensearch import get_temp_file
import os

client = TestClient(app)

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


def test_source_file():
    response = client.post(
        "/prompt/source_file", files=[("file", open(file_path, "rb"))]
    )
    file_id = response.json()["id"]
    prompt_file_path = get_temp_file(file_id)
    assert prompt_file_path
    with open(prompt_file_path) as f:
        assert f.read() == "This is not a real document, it's just a test."
