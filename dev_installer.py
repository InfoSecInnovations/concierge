from launch_concierge.concierge_installer.arguments import install_arguments
from launch_concierge.concierge_installer.functions import (
    init_arguments,
    clean_up_existing,
    prompt_for_parameters,
    prompt_concierge_install,
    do_install,
)
import subprocess
from script_builder.util import get_venv_path
import os

argument_processor = init_arguments(install_arguments)
clean_up_existing()
prompt_for_parameters(argument_processor)
prompt_concierge_install()

# install git commit linter hook
subprocess.run([os.path.join(get_venv_path(), "pre-commit"), "install"])

do_install(argument_processor, "development")
print(
    "\nInstall completed.\nTo start Concierge use the following command: python launch_dev.py\nTo start Concierge in a locally built Docker container use: python launch_local.py\n\n"
)
