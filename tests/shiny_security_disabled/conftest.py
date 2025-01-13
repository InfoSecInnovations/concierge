import pytest
from ..util import destroy_instance
from install_concierge.installer_lib.do_install import do_install
from dotenv import load_dotenv
import os
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
    do_install(InputArguments(), "development", False)
    load_dotenv()
    # we just need OpenSearch to be up (Ollama should already be up after running the installer)
    while not check_opensearch():
        pass
    yield
    destroy_instance()
