import pytest
import requests
import os


@pytest.fixture(scope="session", autouse=True)
def shabti_instance():
    while True:
        try:
            requests.get("https://shabti:15131", verify=os.getenv("ROOT_CA"))
            break
        except Exception:
            continue
    yield
