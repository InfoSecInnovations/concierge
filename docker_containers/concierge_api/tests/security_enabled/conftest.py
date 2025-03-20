import pytest
from app.status import check_opensearch
from load_dotenv import load_env


@pytest.fixture(scope="session", autouse=True)
def working_connection():
    load_env()
    while True:
        try:
            # TODO: ping Keycloak too?
            if check_opensearch():
                return
        except ConnectionError:
            continue
