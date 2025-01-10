import pytest
from ..util import destroy_instance
from install_concierge.installer_lib.do_install import do_install
from dotenv import load_dotenv
import os
import requests
from requests import ConnectionError
from concierge_backend_lib.status import check_opensearch

load_dotenv()


class InputArguments:
    def __init__(self):
        # use saved compute method on this machine if present
        compute_method = (
            "GPU" if os.getenv("OLLAMA_SERVICE", "ollama").endswith("gpu") else "CPU"
        )
        self.parameters = {
            "host": "localhost",
            "port": 15130,
            "security_level": "None",
            "compute_method": compute_method,
            "language_model": "mistral",
        }


@pytest.fixture(scope="session", autouse=True)
def security_disabled_instance():
    destroy_instance()
    do_install(InputArguments(), "development", True)
    load_dotenv()
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
