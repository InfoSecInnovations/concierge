from install_concierge.installer_lib.arguments import install_arguments
from install_concierge.installer_lib import (
    clean_up_existing,
    do_install,
    init_arguments,
    prompt_for_parameters,
    prompt_concierge_install,
)
import subprocess
from script_builder.util import get_venv_path
from concierge_scripts.add_keycloak_demo_users import add_users
import os
import dotenv

argument_processor = init_arguments(install_arguments)
clean_up_existing()
prompt_for_parameters(argument_processor, "python install_dev.py")
prompt_concierge_install()

# install git commit linter hook
subprocess.run([os.path.join(get_venv_path(), "pre-commit"), "install"])

do_install(argument_processor, "development")
if argument_processor.parameters["security_level"].lower() == "demo":
    dotenv.load_dotenv()
    add_users()
print(
    "\nInstall completed.\nTo start Concierge use the following command: python launch_dev.py\nTo start Concierge in a locally built Docker container use: python launch_local.py\n\n"
)
