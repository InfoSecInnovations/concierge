from script_builder.argument_processor import ArgumentData, ArgumentProcessor
from script_builder.util import get_default_directory
import os


def get_base_directory(processor: ArgumentProcessor):
    return os.path.join(
        get_default_directory(processor.parameters["instance_type"] == "standalone"),
        "concierge",
    )


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
            "Please choose 'everyone' (this is the default) or 'standalone' (just you):",
        ],
        input=ArgumentData.InputData(
            default="everyone", options=["everyone", "standalone"]
        ),
    ),
    ArgumentData(
        key="compute_method",
        help="Do you want to use CPU or GPU acceleration?",
        description=[
            "Do you want to use CPU (default) or GPU compute to speed up Concierge responses?"
        ],
        input=ArgumentData.InputData(default="CPU", options=["CPU", "GPU"]),
    ),
    ArgumentData(
        key="language_model",
        help="What language model will this Concierge instance use?",
        description=[
            "Which language model do you want to use? ",
            "note: the current recommended default for Concierge is mistral.",
            "For more info on language models available please go here:",
            "https://ollama.com/library",
        ],
        input=ArgumentData.InputData(default="mistral", prompt="which language model?"),
    ),
    ArgumentData(
        key="activity_logging",
        help="Will this Concierge instance log activity? Strongly suggest setting this!",
        description=[
            "NOTE: this feature is not implemented yet, the current logging options are placeholders!",
            "Logging is a key component of Concierge",
            "We strongly recommend you leave this enabled.",
            "Your logs will remain local to your Concierge instance.",
        ],
        input=ArgumentData.InputData(
            default="True", options=["True", "False"], prompt="logging enabled?"
        ),
    ),
    ArgumentData(
        key="logging_directory",
        condition=show_logging_directory,
        help="Path for logs to be written",
        description=["Where would you like to store the Concierge logs?"],
        input=ArgumentData.InputData(
            default=get_default_log_dir, prompt="log directory location?"
        ),
    ),
    ArgumentData(
        key="log_retention",
        help="How long will logs be kept?",
        description=["How long do you want to keep Concierge activity logs?"],
        input=ArgumentData.InputData(
            default="90", prompt="how many days should logs be retained?"
        ),
    ),
    ArgumentData(
        key="port",
        help="Which port should the Concierge web UI be served on?",
        description=["Which port should the Concierge web UI be served on?"],
        input=ArgumentData.InputData(default="15130", prompt="port?"),
    ),
]
