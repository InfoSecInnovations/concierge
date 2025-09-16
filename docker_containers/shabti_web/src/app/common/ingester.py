from shiny import ui, reactive, render, Inputs, Outputs, Session, module
from tqdm import tqdm
from ..common.text_list import text_list_ui, text_list_server
from typing import AsyncGenerator, Any
from shabti_types import DocumentIngestInfo, UnsupportedFileError
from shabti_api_client import BaseShabtiClient
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
    client: BaseShabtiClient,
    selected_collection: reactive.Value,
):
    file_input_trigger = reactive.value(0)
    url_input_trigger = reactive.value(0)
    ingesting_done = reactive.value(0)
    files_are_ingesting = reactive.value(False)
    url_values = text_list_server("url_input_list", url_input_trigger)

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
    @reactive.event(
        file_input_trigger, files_are_ingesting, ignore_none=False, ignore_init=False
    )
    def file_input():
        if files_are_ingesting.get():
            return ui.markdown("Currently ingesting files...")
        return ui.input_file(id="ingester_files", label=None, multiple=True)

    async def load_doc(stream: AsyncGenerator[DocumentIngestInfo, Any]):
        page_progress = tqdm()
        with ui.Progress(0) as p:
            p.set(0, message="ingesting...")
            async for x in stream:
                if isinstance(x, UnsupportedFileError):
                    ui.notification_show(x.message, type="error")
                    continue
                p.max = x.total
                p.set(
                    x.progress + 1,
                    message=f"{x.label}: part {x.progress + 1} of {x.total}.",
                )
                page_progress.n = x.progress + 1
                page_progress.total = x.total
                page_progress.refresh()
        page_progress.close()

    @reactive.extended_task
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

    @ui.bind_task_button(button_id="ingest")
    @reactive.extended_task
    async def ingest_urls(urls: list[str], collection_id: str):
        print("ingest URLs")
        await load_doc(client.insert_urls(collection_id, urls))
        ui.notification_show("Finished ingesting URLs!")
        print("finished ingesting URLs")

    @reactive.effect
    def ingest_urls_effect():
        ingest_urls.result()
        with reactive.isolate():
            ingesting_done.set(ingesting_done.get() + 1)

    @reactive.effect
    def ingest_files_effect():
        ingest_files.result()
        with reactive.isolate():
            files_are_ingesting.set(False)
            ingesting_done.set(ingesting_done.get() + 1)

    @reactive.effect
    @reactive.event(input.ingester_files, ignore_none=True, ignore_init=True)
    def handle_file_upload():
        files = input.ingester_files()
        if not len(files):
            return
        collection_id = selected_collection.get()
        print(f"ingesting documents into collection {collection_id}")
        file_input_trigger.set(file_input_trigger.get() + 1)
        files_are_ingesting.set(True)
        ingest_files(files, collection_id)

    @reactive.effect
    @reactive.event(input.ingest, ignore_none=False, ignore_init=True)
    def handle_url_ingest_click():
        urls = [value for value in url_values() if value]
        if not urls or not len(urls):
            return
        collection_id = selected_collection.get()
        print(f"ingesting documents into collection {collection_id}")
        url_input_trigger.set(url_input_trigger.get() + 1)
        ingest_urls(urls, collection_id)

    return ingesting_done
