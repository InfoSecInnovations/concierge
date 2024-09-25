import subprocess
import os
from script_builder.util import (
    require_admin,
    prompt_install,
)
from script_builder.argument_processor import ArgumentProcessor
from dotenv import set_key

from .clean_up_existing import clean_up_existing
from .do_install import do_install

__all__ = [
    "clean_up_existing",
    "do_install",
    "init_arguments",
    "prompt_for_parameters",
    "docker_compose_helper",
    "prompt_concierge_install",
    "set_compute",
]


def init_arguments(install_arguments):
    require_admin()
    argument_processor = ArgumentProcessor(install_arguments)
    argument_processor.init_args()
    print("\n\n\nConcierge: AI should be simple, safe, and amazing.\n\n\n")
    return argument_processor


def prompt_for_parameters(argument_processor, command="python install.py"):
    print("Welcome to the Concierge installer.")
    print("Just a few configuration questions and then some download scripts will run.")
    print("Note: you can just hit enter to accept the default option.\n\n")

    argument_processor.prompt_for_parameters()

    print("Concierge setup is almost complete.\n")
    print(
        "If you want to speed up the deployment of future Concierge instances with these exact options, save the command below.\n"
    )
    print(
        "After git clone or unzipping, run this command and you can skip all these questions!\n\n"
    )
    print(f"\n{command} {argument_processor.get_command_parameters()}\n\n\n")

    print("About to make changes to your system.\n")
    # TODO make a download size variable & update based on findings
    # print("Based on your selections, you will be downloading aproximately X of data")
    # print("Depending on network speed, this may take a while")
    print(
        'No changes have yet been made to your system. If you stop now or answer "no", nothing will have changed.'
    )


def docker_compose_helper(environment, is_local=False, rebuild=False):
    filename = "docker-compose"
    if environment == "development":
        filename = f"{filename}-dev"
    if is_local:
        filename = f"{filename}-local"
    full_path = os.path.abspath(os.path.join(os.getcwd(), f"{filename}.yml"))
    if rebuild:
        # pull latest versions
        subprocess.run(["docker", "compose", "-f", full_path, "pull"])
    if is_local:
        # build local concierge image
        subprocess.run(["docker", "compose", "-f", full_path, "build"])
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            full_path,
            "up",
            "-d",
        ]
    )


def prompt_concierge_install():
    prompt_install(
        "Ready to apply settings and start downloading?",
        "Install cancelled. No changes were made. Have a nice day! :-)",
    )


def set_compute(method: str):
    set_key(
        ".env", "OLLAMA_SERVICE", "ollama-gpu" if method.lower() == "gpu" else "ollama"
    )
