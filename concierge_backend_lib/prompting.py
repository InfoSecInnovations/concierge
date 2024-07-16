import json
import requests
import os
from dotenv import load_dotenv
from opensearchpy import OpenSearch
from concierge_backend_lib.embeddings import create_embeddings

load_dotenv()
HOST = os.getenv("OLLAMA_HOST") or "localhost"


def get_context(
    client: OpenSearch, collection_name: str, reference_limit: int, user_input: str
):
    query = {
        "size": reference_limit,
        "query": {
            "knn": {
                "document_vector": {
                    "vector": create_embeddings(user_input),
                    "min_score": 0.8,  # this is quite a magic number, tweak as needed!
                }
            }
        },
        "_source": {"includes": ["page_index", "page_id", "text"]},
    }

    response = client.search(body=query, index=f"{collection_name}.vectors")

    hits = [hit["_source"] for hit in response["hits"]["hits"]]

    page_metadata = {}

    for hit in hits:
        if hit["page_index"] not in page_metadata:
            page_metadata[hit["page_index"]] = {}
        if hit["page_id"] not in page_metadata[hit["page_index"]]:
            response = client.get(hit["page_index"], hit["page_id"])
            page_metadata[hit["page_index"]][hit["page_id"]] = response["_source"]

    doc_metadata = {}

    for item in page_metadata.values():
        for value in item.values():
            if value["doc_index"] not in doc_metadata:
                doc_metadata[value["doc_index"]] = {}
            if value["doc_id"] not in doc_metadata[value["doc_index"]]:
                response = client.get(value["doc_index"], value["doc_id"])
                doc_metadata[value["doc_index"]][value["doc_id"]] = {
                    **response["_source"],
                    "id": value["doc_id"],
                }

    sources = []

    for hit in hits:
        page = page_metadata[hit["page_index"]][hit["page_id"]]
        doc = doc_metadata[page["doc_index"]][page["doc_id"]]
        sources.append(
            {"type": doc["type"], "page_metadata": page, "doc_metadata": doc}
        )

    return {
        "context": "\n".join([hit["text"] for hit in hits]),
        "sources": sources,
    }


def prepare_prompt(
    context,
    task_prompt,
    user_input,
    persona_prompt=None,
    enhancer_prompts=None,
    source_file_contents=None,
):
    prompt = task_prompt

    if persona_prompt:
        prompt = persona_prompt + "\n\n" + prompt

    if enhancer_prompts:
        for enhancer_prompt in enhancer_prompts:
            prompt = prompt + "\n\n" + enhancer_prompt

    prompt = prompt + "\n\nContext: " + context + "\n\nUser input: " + user_input

    if source_file_contents:
        prompt = prompt + "\n\nSource file: " + source_file_contents

    return prompt


def get_response(
    context,
    task_prompt,
    user_input,
    persona_prompt=None,
    enhancer_prompts=None,
    source_file_contents=None,
):
    prompt = prepare_prompt(
        context,
        task_prompt,
        user_input,
        persona_prompt,
        enhancer_prompts,
        source_file_contents,
    )

    data = {"model": "mistral", "prompt": prompt, "stream": False}

    response = requests.post(f"http://{HOST}:11434/api/generate", data=json.dumps(data))

    print(f"Response: {response}")

    if response.status_code != 200:
        return f"ollama status: {response.status_code}"

    return json.loads(response.text)["response"]


def stream_response(
    context,
    task_prompt,
    user_input,
    persona_prompt=None,
    enhancer_prompts=None,
    source_file_contents=None,
):
    prompt = prepare_prompt(
        context,
        task_prompt,
        user_input,
        persona_prompt,
        enhancer_prompts,
        source_file_contents,
    )

    data = {"model": "mistral", "prompt": prompt, "stream": True}

    response = requests.post(f"http://{HOST}:11434/api/generate", data=json.dumps(data))

    for item in response.iter_lines():
        if item:
            value = json.loads(item)
            if "response" in value:
                yield value["response"]
