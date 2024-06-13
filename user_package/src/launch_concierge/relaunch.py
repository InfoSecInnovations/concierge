from launch_concierge.concierge_installer.functions import docker_compose_helper


def relaunch():
    compute_method = (
        input("Start docker containers with CPU or GPU? [CPU] or GPU:") or "CPU"
    )
    if compute_method == "GPU":
        docker_compose_helper("production", "GPU")
    else:
        docker_compose_helper("production", "CPU")


if __name__ == "__main__":
    relaunch()
