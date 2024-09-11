import yaml


def load_config():
    try:
        with open("concierge.yml", "r") as file:
            return yaml.safe_load(file)
    except Exception:
        return None
