# The user install script only configures the Docker environment and containers
from launch_concierge.concierge_installer.arguments import install_arguments
from launch_concierge.concierge_installer import (
    init_arguments,
    prompt_for_parameters,
    prompt_concierge_install,
    clean_up_existing,
    do_install,
    install_demo_users,
)


def install(command="install_concierge"):
    argument_processor = init_arguments(install_arguments)
    clean_up_existing()
    prompt_for_parameters(argument_processor, command)
    prompt_concierge_install()
    do_install(argument_processor, "production")
    if argument_processor.parameters["security_level"].lower() == "demo":
        install_demo_users()
    print(
        f"\nInstall completed. After a couple of minutes you should be able to access the Concierge Web UI at localhost:{argument_processor.parameters['port']}\n"
    )
    print(
        "So long as Docker is running the web UI should be available. If you need to relaunch the containers use this command: python relaunch.py\n\n"
    )


if __name__ == "__main__":
    install("python -m launch_concierge.install")
