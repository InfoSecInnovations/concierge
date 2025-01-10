# import subprocess
from install_concierge.installer_lib import (
    docker_compose_helper,
    set_compute,
)
from install_concierge.installer_lib.concierge_launcher import get_launch_arguments
import argparse
import dotenv
import os
from concierge_backend_lib.authorization import auth_enabled
from shiny import run_app

parser = argparse.ArgumentParser()
parser.add_argument(
    "-e",
    "--environment",
    help="development or [production]",
)
dotenv.load_dotenv()
user_args = get_launch_arguments(parser)
args = parser.parse_args()

environment = args.environment
if environment != "development":
    environment = "production"
compute_method = user_args["compute_method"]
set_compute(compute_method)
docker_compose_helper(
    environment, environment == "production"
)  # the dev version of the production environment builds the image locally

if environment == "production":
    exit()  # in production we use the docker container to host the Shiny app so our work is done here

app_dir = "concierge_shiny"
port = int(os.getenv("WEB_PORT", "15130"))
host = "localhost"

if auth_enabled():
    run_app(
        app_dir=app_dir,
        port=port,
        # reload currently reruns this script instead of the app
        # reload=environment == "development",
        # launch_browser currently doesn't work with HTTPS
        # launch_browser=True,
        host=host,
        ssl_keyfile=os.getenv("WEB_KEY"),
        ssl_certfile=os.getenv("WEB_CERT"),
    )
else:
    run_app(
        app_dir=app_dir,
        port=port,
        # reload currently reruns this script instead of the app
        # reload=environment == "development",
        launch_browser=True,
        host=host,
    )
