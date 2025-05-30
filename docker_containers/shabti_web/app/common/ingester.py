from shiny import ui, reactive, render, Inputs, Outputs, Session, module
from tqdm import tqdm
from ..common.text_list import text_list_ui, text_list_server
from typing import AsyncGenerator, Any
from shabti_types import DocumentIngestInfo
from shabti_api_client import BaseConciergeClient
import os


@module.ui
def ingester_ui():
    return ui.accordion_panel(
        ui.markdown("#### Ingest Documents"),
        ui.output_ui("ingester_content"),
        value="ingest_documents",
    )


@module.server
def ingester_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    client: BaseConciergeClient,
    selected_collection: reactive.Value,
):
    file_input_trigger = reactive.value(0)
    ingesting_done = reactive.value(0)
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

    async def load_doc(stream: AsyncGenerator[DocumentIngestInfo, Any]):
        page_progress = tqdm()
        with ui.Progress(0) as p:
            p.set(0, message="ingesting...")
            async for x in stream:
                p.max = x.total
                p.set(
                    x.progress + 1,
                    message=f"{x.label}: part {x.progress + 1} of {x.total}.",
                )
                page_progress.n = x.progress + 1
                page_progress.total = x.total
                page_progress.refresh()
        page_progress.close()

    async def ingest_files(files: list[dict], collection_id: str):
        print("ingest files")
        # we want to conserve the original file names
        named_files = []
        for file in files:
            named_file = os.path.join(os.path.dirname(file["datapath"]), file["name"])
            os.rename(file["datapath"], named_file)
            named_files.append(named_file)
        await load_doc(client.insert_files(collection_id, named_files))
        ui.notification_show("Finished ingesting files!")
        print("finished ingesting files")

    async def ingest_urls(urls: list[str], collection_id: str):
        print("ingest URLs")
        await load_doc(client.insert_urls(collection_id, urls))
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
    def ingest_effect():
        ingest.result()
        with reactive.isolate():
            ingesting_done.set(ingesting_done.get() + 1)

    @reactive.effect
    @reactive.event(input.ingest, ignore_none=False, ignore_init=True)
    def handle_click():
        urls = list(filter(None, url_values()))
        files = None
        if "ingester_files" in input:
            files = input.ingester_files()
        if (not urls or not len(urls)) and (not files or not len(files)):
            return
        collection_id = selected_collection.get()
        print(f"ingesting documents into collection {collection_id}")
        del input.ingester_files
        file_input_trigger.set(file_input_trigger.get() + 1)
        ingest(files, urls, collection_id)

    return ingesting_done
