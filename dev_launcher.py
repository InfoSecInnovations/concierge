import subprocess
from script_builder.util import get_venv_executable
from launcher_package.src.launch_concierge.concierge_installer.functions import (
    docker_compose_helper,
)
import argparse
import dotenv
import os

parser = argparse.ArgumentParser()
parser.add_argument(
    "-e",
    "--environment",
    help="development or [production]",
)
args = parser.parse_args()

environment = args.environment
if environment != "development":
    environment = "production"

dotenv.load_dotenv()

compute_method = (
    input("Start docker containers with CPU or GPU? [CPU] or GPU:") or "CPU"
)
docker_compose_helper(
    environment, compute_method, environment == "production"
)  # the dev version of the production environment builds the image locally

if environment == "production":
    exit()  # in production we use the docker container to host the Shiny app so our work is done here

subprocess.run(
    [
        get_venv_executable(),
        "-m",
        "shiny",
        "run",
        "--port",
        os.getenv("WEB_PORT", "15130"),
        *(["--reload"] if environment == "development" else []),
        "--launch-browser",
        "concierge_shiny/app.py",
    ]
)
