import os

def auth_enabled():
    return os.getenv("CONCIERGE_SECURITY_ENABLED", "False") == "True"