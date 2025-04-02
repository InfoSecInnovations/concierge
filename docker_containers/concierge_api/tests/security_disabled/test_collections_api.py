from fastapi.testclient import TestClient
from app.app import app
import os

client = TestClient(app)

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


def test_create_collection():
    response = client.post("/collections", json={"collection_name": "test_collection"})
    assert response.status_code == 200
    assert response.json()["collection_id"]
