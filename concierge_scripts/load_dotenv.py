import dotenv
import os
from importlib.resources import files


def load_env():
    dotenv.load_dotenv(
        os.path.join(files(), "..", "bun_installer", "docker_compose", ".env"),
        override=True,
    )
