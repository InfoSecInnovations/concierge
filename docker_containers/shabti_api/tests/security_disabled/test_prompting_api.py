from ...src.app.ingesting import insert_document
import os
from ...src.app.loading import load_file

filename = "prompt_test.md"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


# the main purpose of this test is just to ensure prompting can run without errors as the output isn't expected to be deterministic
async def test_prompt(shabti_client, shabti_collection_id):
    with open(file_path, "rb") as f:
        doc = load_file(f, filename)
        binary = f.read()
    async for _ in insert_document(None, shabti_collection_id, doc, binary):
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
