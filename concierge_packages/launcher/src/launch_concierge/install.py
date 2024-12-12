from script_builder.util import setup_pip, install_package, run_in_venv
from importlib.metadata import version


def install():
    setup_pip()
    install_package(f"install-concierge=={version("launch_concierge")}")
    run_in_venv("install_concierge.install")


if __name__ == "__main__":
    install()
