import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def working_connection():
    while True:
        try:
            requests.get("http://shabti:15131")
            break
        except Exception:
            continue
    yield
