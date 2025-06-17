import pytest
from ...app.status import check_opensearch
from ...load_dotenv import load_env
from ...app.app import create_app
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
