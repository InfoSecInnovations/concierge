# The dev install script configures the Docker environment and containers

from user_package.concierge_installer.arguments import install_arguments
from user_package.concierge_installer.functions import (
    init_arguments,
    clean_up_existing,
    prompt_for_parameters,
    prompt_concierge_install,
    install_docker,
)
import subprocess
from script_builder.util import get_venv_path, setup_pip, install_requirements
import os

argument_processor = init_arguments(install_arguments)
clean_up_existing()
prompt_for_parameters(argument_processor)
prompt_concierge_install()
setup_pip()
install_requirements("dev_requirements.txt")

# install git commit linter hook
subprocess.run([os.path.join(get_venv_path(), "pre-commit"), "install"])

install_docker(argument_processor, "development")
print(
    "\nInstall completed.\nTo start Concierge use the following command: python launch_dev.py\nTo start Concierge in a locally built Docker container use: python launch_local.py\n\n"
)
