import pytest
from app.status import check_opensearch
from load_dotenv import load_env
from .lib import clean_up_collections
import asyncio


@pytest.fixture(scope="session", autouse=True)
def working_connection():
    load_env()
    while True:
        try:
            # TODO: ping Keycloak too?
            if check_opensearch():
                break
        except ConnectionError:
            continue
    yield
    asyncio.run(clean_up_collections())
