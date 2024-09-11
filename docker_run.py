from shiny import run_app

# this script should only be run inside the docker container

run_app(
    app_dir="concierge_shiny",
    port=15130,
    launch_browser=False,
    host="0.0.0.0",
    ssl_keyfile="web_certs/key.pem",
    ssl_certfile="web_certs/cert.pem",
)
