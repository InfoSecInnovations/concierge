import requests
import os
from concierge_backend_lib.opensearch import get_client

OLLAMA_HOST = os.getenv("OLLAMA_HOST") or "localhost"


def check_ollama():
    try:
        return requests.get(f"http://{OLLAMA_HOST}:11434/").status_code == 200
    except Exception:
        return False


def check_opensearch():
    client = get_client()
    return client.ping()
