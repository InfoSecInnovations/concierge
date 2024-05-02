from shiny import ui, reactive, render, Inputs, Outputs, Session, module
import shutil
import os
from tqdm import tqdm
from concierge_backend_lib.ingesting import insert
from concierge_backend_lib.collections import get_existing_collection
from loaders.pdf import load_pdf
from loaders.web import load_web
from util.async_generator import asyncify_generator
from components import collection_selector_ui, collection_selector_server, collection_create_ui, collection_create_server

@module.ui
def loader_ui():
    return [
        ui.markdown("# Loader"),
        ui.output_ui("loader_content")
    ]

@module.server
def loader_server(input: Inputs, output: Outputs, session: Session, upload_dir, selected_collection, collections, milvus_status):

    file_input_trigger = reactive.value(0)
    url_input_ids = reactive.value([])

    collection_selector_server("collection_selector", selected_collection, collections)
    collection_create_server("collection_creator", selected_collection, collections)
    
    @render.ui
    def loader_content():
        if milvus_status.get():
            return ui.TagList(
                collection_selector_ui("collection_selector"),
                collection_create_ui("collection_creator"),
                ui.markdown("### Documents"),
                ui.output_ui("file_input"),
                ui.markdown("### URLs"),
                ui.div(ui.div(id="url_input_list"), id="url_input_list_container"),
                ui.input_task_button(id="ingest", label="Ingest")
            )
        else:
            return ui.markdown("Milvus is offline!")

    @reactive.calc
    def url_values():
        return [input[id]() for id in url_input_ids.get()]
    
    @reactive.effect
    @reactive.event(url_values, ignore_none=False, ignore_init=False)
    def handle_url_inputs():

        # if IDs were deleted, remake the whole input list  
        if not len(url_input_ids.get()):
            ui.remove_ui(selector="#url_input_list_container *", multiple=True, immediate=True)
            ui.insert_ui(
                ui.div(id="url_input_list"),
                selector="#url_input_list_container",
                immediate=True
            )

        # if there's already an empty input we don't need more
        if not all([len(x) > 0 for x in url_values()]):
            return

        # insert new ID and corresponding element if all existing ones have values
        idx = len(url_values())
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
            label=None,
            multiple=True
        )

    async def load_pages(pages, collection, label):
        page_progress = tqdm(total=len(pages))
        with ui.Progress(1, len(pages)) as p:
            p.set(0, message=f"{label}: loading...")
            async for x in asyncify_generator(insert(pages, collection)):
                p.set(x[0] + 1, message=f"{label}: part {x[0] + 1} of {x[1]}.")
                page_progress.n = x[0] + 1
                page_progress.refresh()
        page_progress.close()

    async def ingest_files(files, collection):
        for file in files:
            print(file["name"])
            ui.notification_show(f"Processing {file["name"]}")
            shutil.copyfile(file["datapath"], os.path.join(upload_dir, file["name"]))
            if file["type"] == 'application/pdf':
                pages = load_pdf(upload_dir, file["name"])
                await load_pages(pages, collection, file["name"])
        ui.notification_show("Finished ingesting files!")
        print("finished ingesting files")

    async def ingest_urls(urls, collection):
        for url in urls:
            print(url)
            ui.notification_show(f"Processing {url}")
            pages = load_web(url)
            await load_pages(pages, collection, url)
        ui.notification_show("Finished ingesting URLs!")
        print("finished ingesting URLs")

    @ui.bind_task_button(button_id="ingest")
    @reactive.extended_task
    async def ingest(files, urls, collection):
        if files and len(files):
            await ingest_files(files, collection)
        if urls and len(urls):
            await ingest_urls(urls, collection)

    @reactive.effect
    @reactive.event(input.ingest, ignore_none=False)
    def handle_click():
        urls = list(filter(None, url_values()))
        files = None
        if "loader_files" in input:
            files = input.loader_files()
        if (not urls or not len(urls)) and (not files or not len(files)):
            return
        collection_name = selected_collection.get()
        print(f"ingesting documents into collection {collection_name}")
        collection = get_existing_collection(collection_name)
        file_input_trigger.set(file_input_trigger.get() + 1) 
        for id in url_input_ids.get():
            del input[id]   
        url_input_ids.set([])
        ingest(files, urls, collection)
