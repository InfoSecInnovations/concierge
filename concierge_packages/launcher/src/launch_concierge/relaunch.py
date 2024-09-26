from launch_concierge.concierge_installer import (
    docker_compose_helper,
    set_compute,
)
from launch_concierge.concierge_launcher import get_launch_arguments


def relaunch():
    user_args = get_launch_arguments()
    compute_method = user_args["compute_method"]
    set_compute(compute_method)
    docker_compose_helper("production")


if __name__ == "__main__":
    relaunch()
