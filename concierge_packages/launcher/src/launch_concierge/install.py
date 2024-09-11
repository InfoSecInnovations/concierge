# The user install script only configures the Docker environment and containers
from launch_concierge.concierge_installer.arguments import install_arguments
from launch_concierge.concierge_installer.functions import (
    init_arguments,
    clean_up_existing,
    prompt_for_parameters,
    prompt_concierge_install,
    do_install,
)


def install():
    argument_processor = init_arguments(install_arguments)
    clean_up_existing()
    prompt_for_parameters(argument_processor)
    prompt_concierge_install()
    do_install(argument_processor, "production")
    print(
        f"\nInstall completed. After a couple of minutes you should be able to access the Concierge Web UI at localhost:{argument_processor.parameters['port']}\n"
    )
    print(
        "So long as Docker is running the web UI should be available. If you need to relaunch the containers use this command: python relaunch.py\n\n"
    )


if __name__ == "__main__":
    install()
