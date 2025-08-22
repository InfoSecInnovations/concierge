import uvicorn
from shabti_util import auth_enabled
from logging_config import logging_config
import os
import argparse
from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()

    parser = argparse.ArgumentParser()
    parser.add_argument("--development", action="store_true")
    command_line_args = parser.parse_args()

    args = {}

    if os.getenv("SHABTI_LOGGING_ENABLED") == "True":
        args["log_config"] = logging_config()

    if auth_enabled():
        args["ssl_keyfile"] = "api_certs/key.pem"
        args["ssl_certfile"] = "api_certs/cert.pem"

    uvicorn.run(
        app="src.app.app:app",
        port=15131,
        host="0.0.0.0",
        reload=command_line_args.development,
        **args,
    )
