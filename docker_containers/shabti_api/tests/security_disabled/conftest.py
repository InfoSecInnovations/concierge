import pytest
from ...src.app.status import check_opensearch
from ...src.load_dotenv import load_env
from ...src.app.app import create_app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def shabti_client(security_disabled_instance):
    load_env()
    while True:
        try:
            if check_opensearch():
                break
        except ConnectionError:
            continue
    yield TestClient(create_app())
