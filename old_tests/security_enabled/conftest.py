import pytest
from ..util import destroy_instance, create_instance
from concierge_scripts.load_dotenv import load_env
import requests
from requests import ConnectionError
from app.status import check_opensearch
import os

load_env()


@pytest.fixture(scope="session", autouse=True)
def security_enabled_instance():
    destroy_instance()
    create_instance(enable_security=True, launch_local=True)
    load_env()
    # we need both Shabti and OpenSearch to be up (Ollama should already be up after running the installer)
    while True:
        try:
            requests.get("https://localhost:15130", verify=os.getenv("ROOT_CA"))
            if check_opensearch():
                break
        except ConnectionError:
            continue
    yield
    # destroy_instance()
