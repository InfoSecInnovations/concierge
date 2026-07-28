from shiny import ui, Inputs, Outputs, Session, App, reactive
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.responses import RedirectResponse


class TestError(Exception):
    pass


app_ui = ui.page_auto(ui.input_action_button("trigger_exception", "Trigger Exception"))


def server(input: Inputs, output: Outputs, session: Session):
    @reactive.effect
    @reactive.event(input.trigger_exception, ignore_init=True)
    def raise_exception():
        raise TestError()
        # this causes a ReactiveWarning to be logged to the console
        # I would like some way to handle this globally across the whole app instead of using a try...except in every single call that can raise this exception
        # In the real app it's a lot of functions


shiny_app = App(app_ui, server)


async def handle_test():
    # In an ideal world this would trigger when TestException is raised in the app
    return RedirectResponse("/login")


exception_handlers = {TestError: handle_test}

routes = [
    Mount("/", app=shiny_app),
]

# This doesn't work because the code for reactives catches the exception and logs it to the console
app = Starlette(routes=routes, exception_handlers=exception_handlers)
