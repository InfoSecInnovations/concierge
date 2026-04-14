import requests
import os
from .opensearch import get_client


def check_llm():
    try:
        return (
            requests.get(f"http://{os.getenv("LLM_HOST")}:11434/health").status_code
            == 200
        )
    except Exception:
        return False


def check_opensearch():
    client = get_client()
    return client.ping()
