import pytest
from ..util import destroy_instance
import isi_util.password
from install_concierge.installer_lib.do_install import do_install
from install_concierge.installer_lib.install_demo_users import install_demo_users
from dotenv import load_dotenv
import os
import requests
from requests import ConnectionError

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
            "security_level": "Demo",
            "compute_method": compute_method,
            "language_model": "mistral",
        }


@pytest.fixture(scope="module", autouse=True)
def security_enabled_instance():
    destroy_instance()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(isi_util.password, "getpass", lambda _: "ThisIsJustATest151")
        do_install(InputArguments(), "development", True)
        install_demo_users()
    while True:
        try:
            requests.get("https://localhost:15130", verify=False)
            break
        except ConnectionError:
            continue
    yield
    destroy_instance()
