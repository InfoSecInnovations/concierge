import pytest
from ...app.status import check_opensearch
from ...load_dotenv import load_env


@pytest.fixture(scope="session", autouse=True)
def working_connection(security_disabled_instance):
    load_env()
    while True:
        try:
            if check_opensearch():
                return
        except ConnectionError:
            continue
