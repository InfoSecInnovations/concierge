import pytest
from ...src.app.status import check_opensearch
from ...src.load_dotenv import load_env
from .lib import clean_up_collections
import asyncio
from ...src.app.app import create_app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def shabti_client():
    load_env()
    while True:
        try:
            # TODO: ping Keycloak too?
            if check_opensearch():
                break
        except ConnectionError:
            continue
    yield TestClient(create_app())
    asyncio.run(clean_up_collections())
