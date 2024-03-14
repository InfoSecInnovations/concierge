import requests
from concierge_backend_lib.collections import get_collections
from pymilvus.exceptions import MilvusException

def get_status():
    try:
        ollama_up = requests.get("http://localhost:11434/").status_code == 200
    except:
        ollama_up = False

    try:
        get_collections()
        milvus_up = True
    except MilvusException:
        milvus_up = False

    return {
        "ollama": ollama_up,
        "milvus": milvus_up
    }