import os
from shabti_util import auth_enabled
from shiny import run_app
from load_dotenv import load_env

load_env()
port = int(os.getenv("WEB_PORT", "15130"))
host = "localhost"

if auth_enabled():
    run_app(
        app="app.app:app",
        port=port,
        # reload currently reruns this script instead of the app
        # reload=True,
        # launch_browser currently doesn't work with HTTPS
        # launch_browser=True,
        host=host,
        ssl_keyfile=os.getenv("WEB_KEY"),
        ssl_certfile=os.getenv("WEB_CERT"),
        dev_mode=True,
    )
else:
    run_app(
        app="app.app:app",
        port=port,
        # reload currently reruns this script instead of the app
        # reload=True,
        launch_browser=True,
        host=host,
    )
