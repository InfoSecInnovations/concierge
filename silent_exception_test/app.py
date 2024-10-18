# This is a demo app to show the Shiny team the issue with "SilentException" which is incredibly annoying.
# Pls ignore

from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from asyncio import sleep

app_ui = ui.page_auto(
    ui.markdown("#Testing silent exception"),
    ui.output_ui("silent_exception"),
    ui.output_ui("working_number"),
    ui.markdown("bottom text"),
)


def server(input: Inputs, output: Outputs, session: Session):
    broken_number = reactive.value(1)
    good_number = reactive.value(1)

    @reactive.extended_task
    async def set_number_bad():
        print("setting number to 1/0")
        await sleep(0.2)
        broken_number.set(1 / 0)
        print("number set to 1/0")

    @reactive.extended_task
    async def set_number_good():
        print("setting number to 42")
        await sleep(0.2)
        good_number.set(42)
        print("number set to 42")

    @render.ui
    def silent_exception():
        return ui.markdown(f"number is {broken_number.get()}")

    @render.ui
    def working_number():
        return ui.markdown(f"number is {good_number.get()}")

    @reactive.effect()
    def startup():
        set_number_good()
        set_number_bad()


app = App(app_ui, server)
