import pytest
from ..util import destroy_instance, create_instance
import requests
from requests import ConnectionError
from concierge_backend_lib.status import check_opensearch
from concierge_scripts.load_dotenv import load_env

load_env()


@pytest.fixture(scope="session", autouse=True)
def security_disabled_instance():
    destroy_instance()
    create_instance(enable_security=False, launch_local=True)
    load_env()
    # we need both Concierge and OpenSearch to be up (Ollama should already be up after running the installer)
    while True:
        try:
            requests.get("http://localhost:15130")
            if check_opensearch():
                break
        except ConnectionError:
            continue
    yield
    destroy_instance()
