import requests
import os
from concierge_backend_lib.opensearch import get_client, get_collections

OLLAMA_HOST = os.getenv("OLLAMA_HOST") or "localhost"
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST") or "localhost"


def check_ollama():
    try:
        return requests.get(f"http://{OLLAMA_HOST}:11434/").status_code == 200
    except Exception:
        return False


def check_opensearch():
    try:
        client = get_client()
        get_collections(client)
        return True
    except Exception:
        return False
