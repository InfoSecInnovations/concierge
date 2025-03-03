import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from concierge_backend_lib.authentication import get_keycloak_admin_openid_token
from concierge_backend_lib.authorization import auth_enabled
from concierge_scripts.load_dotenv import load_env

load_env()


def get_token():
    if not auth_enabled():
        return {"access_token": None}
    return get_keycloak_admin_openid_token()
