import platform
import os
import ctypes
import argparse
from dataclasses import dataclass
from collections.abc import Callable

@dataclass
class InstallArgument:
    @dataclass
    class ArgumentInput:
        default: str | Callable[[], str]
        prompt: str | None = None
        options: list[str] | None = None
        
    key: str
    help: str
    description: list[str]
    input: ArgumentInput
    condition: Callable[[], bool] | None = None

# determine os - needed for pathing and other OS specific options
my_platform = platform.platform()

if my_platform == "Linux":
    if os.geteuid() == 0:
        print("Please do not run this script as root or with sudo.")
        print("If needed, this script will prompt for elevated permission.")
        exit()
if my_platform == "Windows":
    if ctypes.windll.shell32.IsUserAnAdmin() != 0:
        print("Please do not run this script as administrator")
        print("If needed, this script will prompt for elevated permission.")
        exit()
# TODO: macOS

install_parameters = {}

def get_docker_directory():
    # set default docker volumes directory
    if my_platform == "Linux":
        #linux stand alone: ~/concierge/volumes
        if install_parameters["instance_type"] == "standalone":
            return "~/concierge/"
        #linux multi user: /opt/concierge/volumes
        return "/opt/concierge/"
    if my_platform == "Windows":
        if install_parameters["instance_type"] == "standalone":
            return os.path.join(os.path.expanduser('~'), "concierge")
        return os.path.join(os.getenv('LOCALAPPDATA'), "concierge")
    # TODO: macOS
    
def get_default_log_dir():
    if my_platform == "Linux":
        if install_parameters["instance_type"] == "standalone":
            return "~/concierge/logs"
        return "/opt/concierge/logs"
    if my_platform == "Windows":
        if install_parameters["instance_type"] == "standalone":
            return os.path.join(os.path.expanduser('~'), "concierge", "logs")
        return os.path.join(os.getenv('LOCALAPPDATA'), "concierge", "logs")
    # TODO: macOS
    
def show_logging_directory():
    return install_parameters["activity_logging"] == "True"

def get_argument_input(input_data: InstallArgument.ArgumentInput):
    input_text = ""
    if callable(input_data.default):
        input_default = input_data.default()
    else:
        input_default = input_data.default
    if input_data.prompt:
        input_text += input_data.prompt + " "
    if input_data.options:
        input_text += " or ".join([f"[{input_option}]" if input_option == input_default else input_option for input_option in input_data.options])
    else: 
        input_text += f"[{input_default}]"
    input_text += ": "
    return input(input_text)

install_arguments = [
    InstallArgument(
        key="instance_type",
        help="Is this Concierge instance for everyone (default) or standalone?",
        description=[
            "Do you want this Concierge instance to be available for everyone on this system or just you?",
            "Please choose 'everyone' (this is the default) or 'standalone' (just you):" 
        ],
        input=InstallArgument.ArgumentInput(
            default="everyone",
            options=["everyone", "standalone"]
        )
    ),
    InstallArgument(
        key="docker_volumes",
        help="Path where this Concierge instance will store data",
        description=[
            "Where do you want your Concierge data to perist?"
        ],
        input=InstallArgument.ArgumentInput(
            default=get_docker_directory,
            prompt="path for data?"
        )
    ),
    InstallArgument(
        key="compute_method",
        help="Do you want to use CPU or GPU acceleration?",
        description=[
            "Do you want to use CPU (default) or GPU compute to speed up Concierge responses?"
        ],
        input=InstallArgument.ArgumentInput(
            default="CPU",
            options=["CPU", "GPU"]
        )
    ),
    InstallArgument(
        key="language_model",
        help="What language model will this Concierge instance use?",
        description=[
            "Which language model do you want to use? ",
            "note: the current recommended default for Concierge is mistral.",
            "For more info on language models available please go here:",
            "https://ollama.com/library"
        ],
        input=InstallArgument.ArgumentInput(
            default="mistral",
            prompt="which language model?"
        )
    ),
    InstallArgument(
        key="activity_logging",
        help="Will this Concierge instance log activity? Strongly suggest setting this!",
        description=[
            "Logging is a key component of Concierge",
            "We strongly recommend you leave this enabled.",
            "Your logs will remain local to your Concierge instance."
        ],
        input=InstallArgument.ArgumentInput(
            default="True",
            options=["True", "False"],
            prompt="logging enabled?"
        )
    ),
    InstallArgument(
        key="logging_directory",
        condition=show_logging_directory,
        help="Path for logs to be written",
        description=[
            "Where would you like to store the Concierge logs?"
        ],
        input=InstallArgument.ArgumentInput(
            default=get_default_log_dir,
            prompt="log directory location?"
        )
    ),
    InstallArgument(
        key="log_retention",
        help="How long will logs be kept?",
        description=[
            "How long do you want to keep Concierge activity logs?"
        ],
        input=InstallArgument.ArgumentInput(
            default="90",
            prompt="how many days should logs be retained?"
        )
    )
]

parser = argparse.ArgumentParser()
for argument in install_arguments:
    parser.add_argument(f"--{argument.key}", help=argument.help)
args = parser.parse_args()
for argument in install_arguments:
    value = getattr(args, argument.key)
    if value:
        install_parameters[argument.key] = value

# message:
print("\n\n\nConcierge: AI should be simple, safe, and amazing.\n\n\n")

print("Welcome to the Concierge installer.")
print("Just a few configuration questions and then some download scripts will run.")
print("Note: you can just hit enter to accept the default option.\n\n")

for index, argument in enumerate(install_arguments):
    print(f"Question {index} of {len(install_arguments)}:")
    if argument.key in install_parameters:
        print("Answer provided by command line argument.")
        continue
    for line in argument.description:
        print(line)
    install_parameters[argument.key] = get_argument_input(argument.input)
    print("\n")
    

