from shiny import run_app
from shabti_util import auth_enabled

# this script should only be run inside the docker container

if auth_enabled():
    run_app(
        app="src.app.app:app",
        port=15130,
        launch_browser=False,
        host="0.0.0.0",
        ssl_keyfile="web_certs/key.pem",
        ssl_certfile="web_certs/cert.pem",
    )
else:
    run_app(app="src.app.app:app", port=15130, launch_browser=False, host="0.0.0.0")
