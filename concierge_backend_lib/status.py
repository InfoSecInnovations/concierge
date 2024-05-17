import requests
from concierge_backend_lib.opensearch import get_client

def check_ollama():
    try:
        return requests.get("http://localhost:11434/").status_code == 200       
    except:
        return False
    
def check_opensearch():
    try:
        get_client()
        return True
    except:
        return False