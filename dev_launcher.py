import subprocess
from script_builder.util import get_venv_executable
from concierge_backend_lib.status import check_ollama, check_opensearch
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

print("Checking Docker container status...\n")
requirements_met = False
if check_ollama():
    print("Ollama running")
    if check_opensearch():
        print("OpenSearch running")
        requirements_met = True
    else:
        print("OpenSearch not found")
else:
    print("Ollama not found")


if not requirements_met:
    print("Docker container dependencies don't appear to be running properly.")
    compute_method = (
        input("Start docker containers with CPU or GPU? [CPU] or GPU:") or "CPU"
    )
    if compute_method == "GPU":
        docker_compose_helper(environment, "GPU")
    else:
        docker_compose_helper(environment, "CPU")


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
