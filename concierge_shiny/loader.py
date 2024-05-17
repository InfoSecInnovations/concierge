from shiny import ui, reactive, render, Inputs, Outputs, Session, module
import shutil
import os
from tqdm import tqdm
from concierge_backend_lib.opensearch import insert
from loaders.pdf import load_pdf
from loaders.web import load_web
from util.async_generator import asyncify_generator
from components import(
    collection_selector_ui, 
    collection_selector_server, 
    collection_create_ui, 
    collection_create_server,
    text_list_ui,
    text_list_server
)

@module.ui
def loader_ui():
    return [
        ui.markdown("# Loader"),
        ui.output_ui("loader_content")
    ]

@module.server
def loader_server(input: Inputs, output: Outputs, session: Session, upload_dir, selected_collection, collections, opensearch_status, client):

    file_input_trigger = reactive.value(0)

    collection_selector_server("collection_selector", selected_collection, collections)
    collection_create_server("collection_creator", selected_collection, collections, client)
    url_values = text_list_server("url_input_list", file_input_trigger)
    
    @render.ui
    def loader_content():
        if opensearch_status.get():
            return ui.TagList(
                collection_selector_ui("collection_selector"),
                collection_create_ui("collection_creator"),
                ui.markdown("### Documents"),
                ui.output_ui("file_input"),
                ui.markdown("### URLs"),
                text_list_ui("url_input_list"),
                ui.input_task_button(id="ingest", label="Ingest")
            )
        else:
            return ui.markdown("Milvus is offline!")

    @render.ui
    @reactive.event(file_input_trigger, ignore_none=False, ignore_init=False)
    def file_input():
        return ui.input_file(
            id="loader_files",
            label=None,
            multiple=True
        )

    async def load_pages(pages, collection_name, label):
        page_progress = tqdm(total=len(pages))
        with ui.Progress(1, len(pages)) as p:
            p.set(0, message=f"{label}: loading...")
            async for x in asyncify_generator(insert(client, collection_name, pages)):
                p.set(x[0] + 1, message=f"{label}: part {x[0] + 1} of {x[1]}.")
                page_progress.n = x[0] + 1
                page_progress.refresh()
        page_progress.close()

    async def ingest_files(files, collection_name):
        os.makedirs(upload_dir, exist_ok=True) # ensure the upload directory exists!
        for file in files:
            print(file["name"])
            ui.notification_show(f"Processing {file['name']}")
            shutil.copyfile(file["datapath"], os.path.join(upload_dir, file["name"]))
            if file["type"] == 'application/pdf':
                pages = load_pdf(upload_dir, file["name"])
                await load_pages(pages, collection_name, file["name"])
        ui.notification_show("Finished ingesting files!")
        print("finished ingesting files")

    async def ingest_urls(urls, collection_name):
        for url in urls:
            print(url)
            ui.notification_show(f"Processing {url}")
            pages = load_web(url)
            await load_pages(pages, collection_name, url)
        ui.notification_show("Finished ingesting URLs!")
        print("finished ingesting URLs")

    @ui.bind_task_button(button_id="ingest")
    @reactive.extended_task
    async def ingest(files, urls, collection_name):
        if files and len(files):
            await ingest_files(files, collection_name)
        if urls and len(urls):
            await ingest_urls(urls, collection_name)

    @reactive.effect
    @reactive.event(input.ingest, ignore_none=False, ignore_init=True)
    def handle_click():
        urls = list(filter(None, url_values()))
        files = None
        if "loader_files" in input:
            files = input.loader_files()
        if (not urls or not len(urls)) and (not files or not len(files)):
            return
        collection_name = selected_collection.get()
        print(f"ingesting documents into collection {collection_name}")
        del input.loader_files
        file_input_trigger.set(file_input_trigger.get() + 1) 
        ingest(files, urls, collection_name)
