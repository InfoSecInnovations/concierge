from shiny import ui, reactive, render, Inputs, Outputs, Session, module
import shutil
import os
from tqdm import tqdm
from concierge_backend_lib.ingesting import insert
from concierge_backend_lib.collections import get_existing_collection
from loaders.pdf import load_pdf
from util.async_generator import asyncify
from components import collection_selector_ui, collection_selector_server

@module.ui
def loader_ui():
    return [
        ui.markdown("# Loader"),
        collection_selector_ui("collection_selector"),
        ui.output_ui("file_input"),
        ui.output_ui("url_inputs"),
        ui.input_task_button(id="ingest", label="Ingest")
    ]

@module.server
def loader_server(input: Inputs, output: Outputs, session: Session, upload_dir, selected_collection, collections):

    file_input_trigger = reactive.value(0)
    url_input_ids = reactive.value(["url_input_0"])

    collection_selector_server("collection_selector", selected_collection, collections)

    @render.ui
    def url_inputs():
        return ui.TagList(
            ui.markdown("### URLs"),
            ui.div(
                ui.input_text("url_input_0", None),
                id="url_input_list"
            )
        )
    
    @reactive.calc
    def url_values():
        return [input[id]() for id in url_input_ids.get()]
    
    @reactive.effect
    @reactive.event(url_values)
    def add_url_input():
        
        idx = len(url_values())
        if not all([len(x) > 0 for x in url_values()]):
            return

        new_id = f"url_input_{idx}"
        
        url_input_ids.set([*url_input_ids.get(), new_id])
        
        ui.insert_ui(
            ui.input_text(new_id, None),
            selector="#url_input_list"
        )

    @render.ui
    @reactive.event(file_input_trigger, ignore_none=False, ignore_init=False)
    def file_input():
        return ui.input_file(
            id="loader_files",
            label="Documents",
            multiple=True
        )

    @ui.bind_task_button(button_id="ingest")
    @reactive.extended_task
    async def ingest_files(files, collection):
        for file in files:
            shutil.copyfile(file["datapath"], os.path.join(upload_dir, file["name"]))
            if file["type"] == 'application/pdf':
                print(file["name"])
                pages = load_pdf(upload_dir, file["name"])
                page_progress = tqdm(total=len(pages))
                with ui.Progress(1, len(pages)) as p:
                    p.set(0, message=f"{file["name"]}: loading...")
                    async for x in asyncify(insert(pages, collection)):
                        p.set(x[0] + 1, message=f"{file["name"]}: page {x[0] + 1} of {x[1]}.")
                        page_progress.n = x[0] + 1
                        page_progress.refresh()
                page_progress.close()
        ui.notification_show("Finished ingesting files!")
        print("finished ingesting files")

    @reactive.effect
    @reactive.event(input.ingest, ignore_none=False)
    def handle_click():
        if "loader_files" in input or "loader_urls" in input:
            collection_name = selected_collection.get()
            print(f"ingesting documents into collection {collection_name}")
            collection = get_existing_collection(collection_name) 
        if "loader_files" in input:
            files = input.loader_files()
            if files and len(files):
                file_input_trigger.set(file_input_trigger.get() + 1)
                ingest_files(files, collection)