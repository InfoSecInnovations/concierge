from shiny import App, ui, Inputs, Outputs, Session, reactive
import time
import asyncio
import concurrent.futures

pool = concurrent.futures.ThreadPoolExecutor()

app_ui = ui.page_auto(ui.markdown("#Testing"))

def server(input: Inputs, output: Outputs, session: Session):

    def progress():
        print("Starting progress!")
        with ui.Progress(0, 4) as p:
            for i in range(4):
                time.sleep(1)
                p.set(i + 1)
        print("Progress done!")

    @reactive.extended_task
    async def init_progress_executor():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(pool, progress)

    @reactive.extended_task
    async def init_progress_to_thread():
        await asyncio.to_thread(progress())

    @reactive.effect
    def init():
        init_progress_to_thread()

app = App(app_ui, server)