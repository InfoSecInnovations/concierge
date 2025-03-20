from .util import destroy_instance, create_instance
from concierge_scripts.load_dotenv import load_env

load_env()

destroy_instance()
create_instance(enable_security=True, launch_local=False)
