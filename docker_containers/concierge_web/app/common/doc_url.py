from urllib.parse import urljoin

API_URL = "http://127.0.0.1:8000/" # TODO: get this from the environment

def doc_url(collection_id: str, doc_type: str, doc_id: str):
    return urljoin(API_URL, f"/files/{collection_id}/{doc_type}/{doc_id}")