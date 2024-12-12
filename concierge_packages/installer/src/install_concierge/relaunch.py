from .installer_lib import (
    docker_compose_helper,
    set_compute,
)
from .installer_lib.concierge_launcher import get_launch_arguments


def relaunch():
    user_args = get_launch_arguments()
    compute_method = user_args["compute_method"]
    set_compute(compute_method)
    docker_compose_helper("production")


if __name__ == "__main__":
    relaunch()
