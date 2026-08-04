from ...src.app.functionality.ingesting import insert_document
import os
from ...src.app.functionality.loading import load_file
from ...src.app.functionality.models import get_models
from uuid import uuid4

filename = "prompt_test.md"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


# the main purpose of this test is just to ensure prompting can run without errors as the output isn't expected to be deterministic
async def test_prompt(shabti_client, shabti_collection_id):
    models = await get_models(tags=["chat"])
    model_name = next(m for m in models["data"] if "default" in m["tags"])["id"]
    unique_filename = uuid4().hex
    with open(file_path, "rb") as f:
        doc = load_file(f, filename)
    async for _ in insert_document(None, shabti_collection_id, doc, unique_filename):
        pass
    response = shabti_client.post(
        "/prompt",
        json={
            "collection_id": shabti_collection_id,
            "task": "question",
            "model_name": model_name,
            "user_input": "What does the word prompting mean?",
        },
    )
    assert response.status_code == 200


# omitting the model name should fall back to the default model
async def test_prompt_without_model_name(shabti_client, shabti_collection_id):
    unique_filename = uuid4().hex
    with open(file_path, "rb") as f:
        doc = load_file(f, filename)
    async for _ in insert_document(None, shabti_collection_id, doc, unique_filename):
        pass
    response = shabti_client.post(
        "/prompt",
        json={
            "collection_id": shabti_collection_id,
            "task": "question",
            "user_input": "What does the word prompting mean?",
        },
    )
    assert response.status_code == 200
