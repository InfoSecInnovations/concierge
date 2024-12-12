from script_builder.util import run_in_venv


def relaunch():
    run_in_venv("install_concierge.relaunch")


if __name__ == "__main__":
    relaunch()
