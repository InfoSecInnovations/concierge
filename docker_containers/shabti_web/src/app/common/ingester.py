from shiny import ui, reactive, render, Inputs, Outputs, Session, module
from tqdm import tqdm
from .text_input_list import text_input_list
from typing import AsyncGenerator, Any
from shabti_types import DocumentIngestInfo, UnsupportedFileError
from shabti_api_client import BaseShabtiClient
from .load_models import load_models
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
    llm_status: reactive.Value,
):
    file_input_trigger = reactive.value(0)
    ingesting_done = reactive.value(0)
    files_are_ingesting = reactive.value(False)
    urls_are_ingesting = reactive.value(False)
    embedding_model_loaded = reactive.value(False)

    @render.ui
    def ingester_content():
        if not llm_status.get():
            return ui.markdown("Waiting for LLM host to come online...")
        if not embedding_model_loaded.get():
            return ui.markdown("Loading embeddings model...")
        return ui.TagList(
            ui.markdown("#### Files"),
            ui.output_ui("file_input"),
            ui.markdown("#### URLs"),
            ui.output_ui("url_input"),
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

    @render.ui
    @reactive.event(urls_are_ingesting, ignore_none=False, ignore_init=False)
    def url_input():
        if urls_are_ingesting.get():
            return ui.markdown("Currently ingesting URLs...")
        return text_input_list("url_input_list")

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
            urls_are_ingesting.set(False)
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
        urls = input.url_input_list()
        if not urls or not len(urls):
            return
        collection_id = selected_collection.get()
        print(f"ingesting documents into collection {collection_id}")
        urls_are_ingesting.set(True)
        ingest_urls(urls, collection_id)

    @reactive.extended_task
    async def load_embedding_model():
        models = await client.get_models()
        embeddings = next(m for m in models["data"] if "embeddings" in m["tags"])
        await load_models(client, embeddings["id"])

    @reactive.effect
    def load_model_effect():
        load_embedding_model.result()
        embedding_model_loaded.set(True)

    @reactive.effect
    def init():
        if llm_status.get() and not embedding_model_loaded.get():
            load_embedding_model()

    return ingesting_done
