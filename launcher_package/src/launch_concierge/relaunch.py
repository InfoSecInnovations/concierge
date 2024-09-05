from launch_concierge.concierge_installer.functions import (
    docker_compose_helper,
    set_compute,
)


def relaunch():
    compute_method = (
        input("Start docker containers with CPU or GPU? [CPU] or GPU:") or "CPU"
    )
    set_compute(compute_method)
    docker_compose_helper("production")


if __name__ == "__main__":
    relaunch()
