import os


def auth_enabled():
    return os.getenv("SHABTI_SECURITY_ENABLED", "False") == "True"
