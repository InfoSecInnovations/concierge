from shiny import ui, reactive, render, Inputs, Outputs, Session, module
import shutil
import os
import asyncio
from tqdm import tqdm
from concierge_backend_lib.ingesting import insert
from loaders.pdf import load_pdf

@module.ui
def loader_ui():
    return [
        ui.markdown("# Loader"),
        # TODO: collection select
        ui.output_ui("file_input"),
        ui.input_task_button(id="ingest", label="Ingest")
    ]

@module.server
def loader_server(input: Inputs, output: Outputs, session: Session, collection, upload_dir):

    file_input_trigger = reactive.value(0)

    @render.ui
    @reactive.event(file_input_trigger, ignore_none=False, ignore_init=False)
    def file_input():
        return ui.input_file(
            id="loader_files",
            label="Documents",
            multiple=True
        )

    def ingest_files(files):
        for file in files:
            shutil.copyfile(file["datapath"], os.path.join(upload_dir, file["name"]))
            if file["type"] == 'application/pdf':
                print(file["name"])
                pages = load_pdf(upload_dir, file["name"])
                page_progress = tqdm(total=len(pages))
                with ui.Progress(1, len(pages)) as p:
                    p.set(0, message=f"{file["name"]}: loading...")
                    for x in insert(pages, collection):
                        p.set(x[0] + 1, message=f"{file["name"]}: page {x[0] + 1} of {x[1]}.")
                        page_progress.n = x[0] + 1
                        page_progress.refresh()
                page_progress.close()

    @ui.bind_task_button(button_id="ingest")
    @reactive.extended_task
    async def ingester_async(files):
        await asyncio.to_thread(ingest_files(files))

    @reactive.effect
    @reactive.event(input.ingest, ignore_none=False)
    def handle_click():
        if "loader_files" in input:
            files = input.loader_files()
            if files and len(files):
                file_input_trigger.set(file_input_trigger.get() + 1)       
                ingester_async(files)