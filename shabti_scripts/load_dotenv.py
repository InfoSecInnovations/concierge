import dotenv
import os
from importlib.resources import files


def load_env():
    dotenv.load_dotenv(
        os.path.join(files(), "..", "shabti_configurator", "docker_compose", ".env"),
        override=True,
    )
