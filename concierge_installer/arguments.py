from script_builder.argument_processor import ArgumentData, ArgumentProcessor
from script_builder.util import get_default_directory
import os

def get_base_directory(processor: ArgumentProcessor):
    return os.path.join(get_default_directory(processor.parameters["instance_type"] == "standalone"), "concierge")

def get_docker_directory(processor: ArgumentProcessor):
    return get_base_directory(processor)
    
def get_default_log_dir(processor: ArgumentProcessor):
    return os.path.join(get_base_directory(processor), "logs")
    
def show_logging_directory(processor: ArgumentProcessor):
    return processor.parameters["activity_logging"] == "True"

install_arguments = [
    ArgumentData(
        key="instance_type",
        help="Is this Concierge instance for everyone (default) or standalone?",
        description=[
            "Do you want this Concierge instance to be available for everyone on this system or just you?",
            "Please choose 'everyone' (this is the default) or 'standalone' (just you):" 
        ],
        input=ArgumentData.InputData(
            default="everyone",
            options=["everyone", "standalone"]
        )
    ),
    ArgumentData(
        key="docker_volumes",
        help="Path where this Concierge instance will store data",
        description=[
            "Where do you want your Concierge data to perist?"
        ],
        input=ArgumentData.InputData(
            default=get_docker_directory,
            prompt="path for data?"
        )
    ),
    ArgumentData(
        key="compute_method",
        help="Do you want to use CPU or GPU acceleration?",
        description=[
            "Do you want to use CPU (default) or GPU compute to speed up Concierge responses?"
        ],
        input=ArgumentData.InputData(
            default="CPU",
            options=["CPU", "GPU"]
        )
    ),
    ArgumentData(
        key="language_model",
        help="What language model will this Concierge instance use?",
        description=[
            "Which language model do you want to use? ",
            "note: the current recommended default for Concierge is mistral.",
            "For more info on language models available please go here:",
            "https://ollama.com/library"
        ],
        input=ArgumentData.InputData(
            default="mistral",
            prompt="which language model?"
        )
    ),
    ArgumentData(
        key="opensearch_password",
        help="Admin password for the OpenSearch instance",
        description=[
            "Please pick the admin password for your OpenSearch instance.",
            "You must pick a strong password otherwise the OpenSearch container will shut down.",
            "Visit https://lowe.github.io/tryzxcvbn/ to evaluate password strength.",
            "Please note that in the current version of Concierge this is stored in plaintext in the .env file, so it isn't actually secure!",
            "We will be introducing proper credential handling in future versions."
        ],
        input=ArgumentData.InputData(
            prompt="OpenSearch admin password?"
        )
    ),
    ArgumentData(
        key="activity_logging",
        help="Will this Concierge instance log activity? Strongly suggest setting this!",
        description=[
            "Logging is a key component of Concierge",
            "We strongly recommend you leave this enabled.",
            "Your logs will remain local to your Concierge instance."
        ],
        input=ArgumentData.InputData(
            default="True",
            options=["True", "False"],
            prompt="logging enabled?"
        )
    ),
    ArgumentData(
        key="logging_directory",
        condition=show_logging_directory,
        help="Path for logs to be written",
        description=[
            "Where would you like to store the Concierge logs?"
        ],
        input=ArgumentData.InputData(
            default=get_default_log_dir,
            prompt="log directory location?"
        )
    ),
    ArgumentData(
        key="log_retention",
        help="How long will logs be kept?",
        description=[
            "How long do you want to keep Concierge activity logs?"
        ],
        input=ArgumentData.InputData(
            default="90",
            prompt="how many days should logs be retained?"
        )
    )
]