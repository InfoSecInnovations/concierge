from script_builder.argument_processor import ArgumentData, ArgumentProcessor
from concierge_util import load_config

arguments = [
    ArgumentData(
        key="compute_method",
        help="Do you want to use CPU or GPU acceleration?",
        description=[
            "Do you want to use CPU (default) or GPU compute to speed up Concierge responses?"
        ],
        default="CPU",
        options=["CPU", "GPU"],
        case_sensitive=False,
    )
]


def get_launch_arguments(parser=None):
    argument_processor = ArgumentProcessor(arguments)
    argument_processor.init_args(parser)
    config = load_config()
    argument_processor.prompt_for_parameters(
        config["previous_parameters"]
        if config and "previous_parameters" in config
        else None
    )
    if not config:
        config = {}
    if "previous_parameters" not in config:
        config["previous_parameters"] = {}
    for key, value in argument_processor.get_saved_inputs().items():
        config["previous_parameters"][key] = value
    return argument_processor.parameters
