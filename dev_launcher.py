# import subprocess
# from script_builder.util import get_venv_executable
from launcher_package.src.launch_concierge.concierge_installer.functions import (
    docker_compose_helper,
    set_compute,
)
import argparse
import dotenv
import os
from shiny import run_app

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
set_compute(compute_method)
docker_compose_helper(
    environment, environment == "production"
)  # the dev version of the production environment builds the image locally

if environment == "production":
    exit()  # in production we use the docker container to host the Shiny app so our work is done here

run_app(
    app_dir="concierge_shiny",
    port=int(os.getenv("WEB_PORT", "15130")),
    # reload currently reruns this script instead of the app
    # reload=environment == "development",
    # launch_browser currently doesn't work with HTTPS
    # launch_browser=True,
    host="localhost",
    ssl_keyfile="test_certs/key.pem",
    ssl_certfile="test_certs/cert.pem",
)

# subprocess.run(
#     [
#         get_venv_executable(),
#         "-m",
#         "shiny",
#         "run",
#         "--port",
#         os.getenv("WEB_PORT", "15130"),
#         *(["--reload"] if environment == "development" else []),
#         "--launch-browser",
#         "--ssl-keyfile",
#         "test_certs/key.pem",
#         "--ssl-certfile",
#         "test_certs/cert.pem",
#         "concierge_shiny/app.py"
#     ]
# )
