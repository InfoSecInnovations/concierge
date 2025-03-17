import os
from importlib.resources import files
from configobj import ConfigObj


def load_prompter_config(dir):
    config_dir = os.path.join(files(), "..", "prompter_config", dir)
    contents = os.listdir(config_dir)
    return {
        file.replace(".concierge", ""): ConfigObj(
            os.path.join(config_dir, file), list_values=False
        )
        for file in filter(lambda file: file.endswith(".concierge"), contents)
    }
