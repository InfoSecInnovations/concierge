from script_builder.argument_processor import ArgumentData, ArgumentProcessor
from script_builder.util import get_default_directory
from concierge_util.config import load_config
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
    return processor.parameters["activity_logging"]


def security_config_exists(processor: ArgumentProcessor):
    config = load_config()
    return (
        config
        and "auth" in config
        and "openid" in config["auth"]
        and len(config["auth"]["openid"])
    )


def can_enable_openid(processor: ArgumentProcessor):
    return not processor.parameters[
        "disable_auth"
    ]  # if we just disabled authentication don't configure OpenID


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
        key="disable_auth",
        help="Remove existing authentication configuration?",
        condition=security_config_exists,
        description=[
            "A config file was detected with authentication already configured.",
            'If you wish to keep the configuration present in this file select "No"',
        ],
        default=False,
        prompt="Remove existing authentication configuration?",
        output_type=ArgumentData.OutputType.bool,
    ),
    ArgumentData(
        key="enable_openid",
        help="Configure OpenID authentication?",
        condition=can_enable_openid,
        description=[
            "You can use OpenID to provide user authentication with Concierge.",
            "It's currently the only supported authentication platform.",
            "You will be required to register an app with an OpenID provider to use this option.",
            "If you already have an OpenID configuration set up this option will allow you to overwrite or add to it.",
        ],
        default=False,
        prompt="Configure OpenID?",
        output_type=ArgumentData.OutputType.bool,
    ),
    ArgumentData(
        key="port",
        help="Which port should the Concierge web UI be served on?",
        description=["Which port should the Concierge web UI be served on?"],
        default=15130,
        prompt="port?",
        output_type=ArgumentData.OutputType.int,
    ),
]
