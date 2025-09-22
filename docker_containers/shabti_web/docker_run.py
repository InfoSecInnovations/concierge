from shiny import run_app
from shabti_util import auth_enabled
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", action="store_true")
    command_line_args = parser.parse_args()
    is_dev = command_line_args.development

    args = {}

    if auth_enabled():
        args["ssl_keyfile"] = "/web_certs/key.pem"
        args["ssl_certfile"] = "/web_certs/cert.pem"

    run_app(
        app="src.app.app:app",
        port=15130,
        launch_browser=False,
        host="0.0.0.0",
        reload=is_dev,
        **args,
    )
