from shiny import ui, reactive, render, Inputs, Outputs, Session, module
from tqdm import tqdm
from concierge_backend_lib.ingesting import insert
from concierge_backend_lib.loading import load_file
from loaders.web import WebLoader
from loaders.base_loader import ConciergeDocument
from isi_util.async_generator import asyncify_generator
from components import (
    collection_selector_server,
    collection_create_server,
    text_list_ui,
    text_list_server,
)
from opensearchpy import OpenSearch


@module.ui
def ingester_ui():
    return ui.accordion_panel(
        ui.markdown("#### Ingest Documents"), ui.output_ui("ingester_content")
    )


@module.server
def ingester_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    selected_collection,
    collections,
    client: OpenSearch,
):
    file_input_trigger = reactive.value(0)
    ingesting_done = reactive.value(0)

    collection_selector_server("collection_selector", selected_collection, collections)
    collection_create_server(
        "collection_creator", selected_collection, collections, client
    )
    url_values = text_list_server("url_input_list", file_input_trigger)

    @render.ui
    def ingester_content():
        return ui.TagList(
            ui.markdown("#### Files"),
            ui.output_ui("file_input"),
            ui.markdown("#### URLs"),
            text_list_ui("url_input_list"),
            ui.input_task_button(id="ingest", label="Ingest"),
        )

    @render.ui
    @reactive.event(file_input_trigger, ignore_none=False, ignore_init=False)
    def file_input():
        return ui.input_file(id="ingester_files", label=None, multiple=True)

    async def load_doc(
        doc: ConciergeDocument,
        collection_name: str,
        label: str,
        binary: bytes | None = None,
    ):
        page_progress = tqdm(total=len(doc.pages))
        with ui.Progress(0, len(doc.pages)) as p:
            p.set(0, message=f"{label}: loading...")
            async for x in asyncify_generator(
                insert(client, collection_name, doc, binary)
            ):
                p.set(x[0] + 1, message=f"{label}: part {x[0] + 1} of {x[1]}.")
                page_progress.n = x[0] + 1
                page_progress.refresh()
        page_progress.close()

    async def ingest_files(files: list[dict], collection_name: str):
        for file in files:
            print(file["name"])
            ui.notification_show(f"Processing {file['name']}")
            with open(file["datapath"], "rb") as f:
                binary = f.read()
            doc = load_file(file["datapath"])
            doc.metadata.filename = file["name"]
            if doc:
                await load_doc(doc, collection_name, file["name"], binary)
        ui.notification_show("Finished ingesting files!")
        print("finished ingesting files")

    async def ingest_urls(urls: list[str], collection_name: str):
        for url in urls:
            print(url)
            ui.notification_show(f"Processing {url}")
            doc = WebLoader.load(url)
            await load_doc(doc, collection_name, url)
        ui.notification_show("Finished ingesting URLs!")
        print("finished ingesting URLs")

    @ui.bind_task_button(button_id="ingest")
    @reactive.extended_task
    async def ingest(files, urls, collection_name, ingesting_index):
        if files and len(files):
            await ingest_files(files, collection_name)
        if urls and len(urls):
            await ingest_urls(urls, collection_name)
        ingesting_done.set(ingesting_index + 1)

    @reactive.effect
    @reactive.event(input.ingest, ignore_none=False, ignore_init=True)
    def handle_click():
        urls = list(filter(None, url_values()))
        files = None
        if "ingester_files" in input:
            files = input.ingester_files()
        if (not urls or not len(urls)) and (not files or not len(files)):
            return
        collection_name = selected_collection.get()
        print(f"ingesting documents into collection {collection_name}")
        del input.ingester_files
        file_input_trigger.set(file_input_trigger.get() + 1)
        # we have to pass reactive reads into an async function rather than calling from within
        ingest(files, urls, collection_name, ingesting_done.get())

    return ingesting_done
