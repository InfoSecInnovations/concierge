from launch_concierge.concierge_installer.functions import docker_compose_helper
from importlib.resources import files


def relaunch():
    compute_method = (
        input("Start docker containers with CPU or GPU? [CPU] or GPU:") or "CPU"
    )
    if compute_method == "GPU":
        docker_compose_helper("production", files(), "GPU")
    else:
        docker_compose_helper("production", files(), "CPU")


if __name__ == "__main__":
    relaunch()
