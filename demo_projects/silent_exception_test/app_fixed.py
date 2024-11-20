# This is the response from the dev team about the proper way to implement the app with extended tasks

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
        return 1 / 0

    @reactive.effect()
    def _():
        x = set_number_bad.result()
        broken_number.set(x)
        print(f"number set to {x}")

    @reactive.extended_task
    async def set_number_good():
        print("setting number to 42")
        await sleep(0.2)
        return 42

    @reactive.effect()
    def _():
        x = set_number_good.result()
        good_number.set(x)
        print(f"number set to {x}")

    @render.ui
    def silent_exception():
        x = broken_number.get()
        return ui.markdown(f"number is {x}")

    @render.ui
    def working_number():
        return ui.markdown(f"number is {good_number.get()}")

    @reactive.effect()
    def startup():
        set_number_good()
        set_number_bad()


app = App(app_ui, server)
