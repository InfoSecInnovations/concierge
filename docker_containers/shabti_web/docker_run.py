from shiny import run_app
from shabti_util import auth_enabled
from glob import glob
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

    if is_dev:
        # the reloader watches its directories recursively and uvicorn hands watchfiles no filter,
        # so a watched directory must never contain the .venv: docker-compose-dev.yml forces
        # polling (inotify doesn't cross Windows bind mounts), which means stat-ing every file in
        # the tree on every tick, and the virtualenv is big enough to exhaust the container's
        # memory at launch. app_dir has to be dropped along with it, because shiny appends app_dir
        # to reload_dirs whenever reload is on and it defaults to the working directory, where the
        # .venv lives - uvicorn then prunes any watched directory nested inside another, collapsing
        # the list straight back to the working directory. app_dir only exists to put the app on
        # sys.path, and this script's own directory is already sys.path[0].
        args["app_dir"] = None
        # the shared packages are bind mounted outside the app directory, so they have to be listed
        # to hot-reload at all. Each package's src is listed rather than /app/python_packages itself
        # because a package can have its own .venv in there (isi_util does)
        args["reload_dirs"] = [
            "/app/shabti_web/src",
            *sorted(glob("/app/python_packages/*/src")),
        ]

    run_app(
        app="src.app.app:app",
        port=15130,
        launch_browser=False,
        host="0.0.0.0",
        reload=is_dev,
        **args,
    )
