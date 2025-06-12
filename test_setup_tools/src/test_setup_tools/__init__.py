import pytest
from .util import destroy_instance, create_instance
from shabti_scripts.load_dotenv import load_env


@pytest.fixture(scope="session")
def security_enabled_instance():
    load_env()
    destroy_instance()
    create_instance(enable_security=True, launch_local=False)
    yield


@pytest.fixture(scope="session")
def security_disabled_instance():
    load_env()
    destroy_instance()
    create_instance(enable_security=False, launch_local=False)
    yield
