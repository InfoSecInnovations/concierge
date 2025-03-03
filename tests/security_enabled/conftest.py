import pytest
from ..util import destroy_instance, create_instance
from concierge_scripts.load_dotenv import load_env
from requests import ConnectionError
from concierge_backend_lib.status import check_opensearch

load_env()


@pytest.fixture(scope="session", autouse=True)
def security_enabled_instance():
    destroy_instance()
    create_instance(enable_security=True, launch_local=False)
    load_env()
    # we need OpenSearch to be up (Ollama should already be up after running the installer)
    while True:
        try:
            if check_opensearch():
                break
        except ConnectionError:
            continue
    yield
    # destroy_instance()
