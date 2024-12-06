from script_builder.argument_processor import ArgumentData, ArgumentProcessor
from script_builder.util import get_default_directory
import os


def get_base_directory(processor: ArgumentProcessor):
    return os.path.join(
        get_default_directory(
            processor.parameters["instance_type"].lower() == "standalone"
        ),
        "concierge",
    )


def get_default_log_dir(processor: ArgumentProcessor):
    return os.path.join(get_base_directory(processor), "logs")


def logging_enabled(processor: ArgumentProcessor):
    return (
        "activity_logging" in processor.parameters
        and processor.parameters["activity_logging"]
    )


install_arguments = [
    ArgumentData(
        key="instance_type",
        help="Is this Concierge instance for everyone (default) or standalone?",
        description=[
            "Do you want this Concierge instance to be available for everyone on this system or just you?",
            "Please choose 'everyone' (this is the default) or 'standalone' (just you):",
        ],
        default="everyone",
        options=["everyone", "standalone"],
        case_sensitive=False,
    ),
    ArgumentData(
        key="compute_method",
        help="Do you want to use CPU or GPU acceleration?",
        description=[
            "Do you want to use CPU (default) or GPU compute to speed up Concierge responses?"
        ],
        default="CPU",
        options=["CPU", "GPU"],
        case_sensitive=False,
    ),
    ArgumentData(
        key="language_model",
        help="What language model will this Concierge instance use?",
        description=[
            "NOTE: this feature is not implement yet, Concierge will always use mistral, model selection coming soon™!",
            "Which language model do you want to use? ",
            "note: the current recommended default for Concierge is mistral.",
            "For more info on language models available please go here:",
            "https://ollama.com/library",
        ],
        default="mistral",
        prompt="which language model?",
        case_sensitive=True,
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
        default=True,
        prompt="logging enabled?",
        output_type=ArgumentData.OutputType.bool,
    ),
    ArgumentData(
        key="logging_directory",
        condition=logging_enabled,
        help="Path for logs to be written",
        description=["Where would you like to store the Concierge logs?"],
        default=get_default_log_dir,
        prompt="log directory location?",
        case_sensitive=True,
    ),
    ArgumentData(
        key="log_retention",
        condition=logging_enabled,
        help="How long will logs be kept?",
        description=["How long do you want to keep Concierge activity logs?"],
        default=90,
        prompt="how many days should logs be retained?",
        output_type=ArgumentData.OutputType.int,
    ),
    ArgumentData(
        key="host",
        help="Which host IP/name will you be using to access the Concierge web UI?",
        description=[
            "Which host IP/name will you be using to access the Concierge web UI?",
            "Keep the default setting if you're using Concierge locally.",
        ],
        default="localhost",
        prompt="host?",
        case_sensitive=True,
    ),
    ArgumentData(
        key="port",
        help="Which port should the Concierge web UI be served on?",
        description=["Which port should the Concierge web UI be served on?"],
        default=15130,
        prompt="port?",
        output_type=ArgumentData.OutputType.int,
    ),
    ArgumentData(
        key="security_level",
        help="Enable login and access controls for Concierge?",
        description=[
            "Enable login and access controls for Concierge?",
            "If you don't do this anyone with access to this machine and/or the web UI will have full privileges to manage and use all data in Concierge.",
            "We recommend enabling security if this isn't a development or test instance.",
            'If you select "Demo", you will be able to try out the RBAC features Concierge ships with, but you should never use this setting in a production environment!',
        ],
        default="None",
        options=["None", "Demo", "Enabled"],
        prompt="Security Level?",
        case_sensitive=False,
        output_type=ArgumentData.OutputType.string,
    ),
]
