import requests
import os
from concierge_backend_lib.opensearch import get_client


def ollama_host():
    return os.getenv("OLLAMA_HOST") or "localhost"


def check_ollama():
    try:
        return requests.get(f"http://{ollama_host()}:11434/").status_code == 200
    except Exception:
        return False


def check_opensearch():
    client = get_client()
    return client.ping()
