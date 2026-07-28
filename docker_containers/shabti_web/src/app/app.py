from starlette.applications import Starlette
from .security_disabled_app.app import app as security_disabled_app
from .security_enabled_app.app import app as security_enabled_app
from starlette.routing import Mount
from shabti_util import auth_enabled

auth_is_enabled = auth_enabled()

routes = [
    Mount("/", app=security_enabled_app if auth_is_enabled else security_disabled_app),
]


app = Starlette(routes=routes)
