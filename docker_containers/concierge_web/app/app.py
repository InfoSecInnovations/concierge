from starlette.applications import Starlette
from .security_disabled_app.app import app as security_disabled_app
from starlette.routing import Mount

routes = [
    Mount("/", app=security_disabled_app),
]


app = Starlette(routes=routes)