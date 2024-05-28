from concierge_installer.arguments import install_arguments
from concierge_installer.functions import (
    init_arguments,
    clean_up_existing,
    prompt_for_parameters,
    start_install,
    finish_install,
)
import subprocess
from script_builder.util import get_venv_executable, get_venv_path
import os

argument_processor = init_arguments(install_arguments)
clean_up_existing()
prompt_for_parameters(argument_processor)
start_install(argument_processor, "development")

# install dev requirements
working_dir = os.getcwd()
subprocess.run(
    [
        get_venv_executable(),
        "-m",
        "pip",
        "install",
        "-r",
        os.path.abspath("dev_requirements.txt"),
    ],
    cwd=working_dir,
)

# install git commit linter hook
subprocess.run(
    [os.path.join(get_venv_path(), "pre-commit"), "install"],
    cwd=working_dir,
)

finish_install(argument_processor)
