import pytest
from ..util import destroy_instance, create_instance
from concierge_backend_lib.status import check_opensearch
from concierge_scripts.load_dotenv import load_env

load_env()


@pytest.fixture(scope="session", autouse=True)
def security_disabled_instance():
    destroy_instance()
    # We're going to run the shiny app from pytest not Docker
    create_instance(enable_security=False, launch_local=False)
    load_env()
    # we just need OpenSearch to be up (Ollama should already be up after running the installer)
    while not check_opensearch():
        pass
    yield
    destroy_instance()
