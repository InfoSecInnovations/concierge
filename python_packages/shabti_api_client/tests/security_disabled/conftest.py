import pytest
import requests
from shabti_api_client import ShabtiClient


@pytest.fixture(scope="session", autouse=True)
def shabti_client():
    while True:
        try:
            requests.get("http://shabti:15131")
            break
        except Exception:
            continue
    yield ShabtiClient("http://shabti:15131")
