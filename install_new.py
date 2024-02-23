import platform
import os
from script_builder.util import disallow_admin
from script_builder.argument_processor import ArgumentProcessor, InstallArgument

# determine os - needed for pathing and other OS specific options
my_platform = platform.system()

disallow_admin()

def get_base_directory(processor: ArgumentProcessor):
    # set default docker volumes directory
    if my_platform == "Linux":
        if processor.install_parameters["instance_type"] == "standalone":
            return "~/concierge/"
        return "/opt/concierge/"
    if my_platform == "Windows":
        if processor.install_parameters["instance_type"] == "standalone":
            return os.path.join(os.getenv('LOCALAPPDATA'), "concierge")
        return "C:\ProgramData\concierge"
    # TODO: macOS

def get_docker_directory(processor: ArgumentProcessor):
    return get_base_directory(processor)
    
def get_default_log_dir(processor: ArgumentProcessor):
    return os.path.join(get_base_directory(processor), "logs")
    
def show_logging_directory(processor: ArgumentProcessor):
    return processor.install_parameters["activity_logging"] == "True"

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

argument_processor = ArgumentProcessor(install_arguments)

argument_processor.init_args()

# message:
print("\n\n\nConcierge: AI should be simple, safe, and amazing.\n\n\n")

print("Welcome to the Concierge installer.")
print("Just a few configuration questions and then some download scripts will run.")
print("Note: you can just hit enter to accept the default option.\n\n")

argument_processor.prompt_for_parameters()
    

