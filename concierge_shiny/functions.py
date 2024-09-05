from shiny import ui
from concierge_backend_lib.ollama import load_model
from tqdm import tqdm
from isi_util.async_generator import asyncify_generator
import humanize


def doc_url(collection_name, doc_type, doc_id):
    return f"/files/{collection_name}/{doc_type}/{doc_id}"


def md_link(url, text=None):
    if text:
        return f'[{text}](<{url}>){{target="_blank"}}'
    return f'<{url}>{{target="_blank"}}'


def page_link(collection_name, page):
    doc_metadata = page["doc_metadata"]
    page_metadata = page["page_metadata"]
    if page["type"] == "pdf":
        return f'PDF File: {md_link(
            f"{doc_url(collection_name, page["type"], doc_metadata["id"])}#page={page_metadata["page"]}", 
            f"page {page_metadata["page"]} of {doc_metadata["filename"]}"
        )}'
    if page["type"] == "web":
        return f'Web page: {md_link(page_metadata["source"])} scraped {doc_metadata["ingest_date"]} from parent URL {md_link(doc_metadata["source"])}'
    if "filename" in doc_metadata:
        return f'{doc_metadata["extension"]} file {md_link(
            doc_url(collection_name, doc_metadata["type"], doc_metadata["id"]),
            doc_metadata["filename"]
        )}'
    return f'{doc_metadata["type"]} type document from {doc_metadata["source"]}'


def doc_link(collection_name, doc):
    if doc["type"] == "pdf":
        return f'PDF File: {md_link(
            doc_url(collection_name, doc["type"], doc["id"]),
            doc["filename"]
        )}'
    if doc["type"] == "web":
        return f'Web page: {md_link(doc["source"])}'
    if "filename" in doc:
        return f'{doc["extension"] if "extension" in doc else doc["type"]} file {md_link(
            doc_url(collection_name, doc["type"], doc["id"]),
            doc["filename"]
        )}'
    return f'{doc["type"]} type document from {doc["source"]}'


async def load_llm_model(model_name):
    print(f"Checking {model_name} language model...")
    pbar = None
    with ui.Progress() as p:
        p.set(value=0, message=f"Loading {model_name} Language Model...")
        async for progress in asyncify_generator(load_model(model_name)):
            if not pbar:
                pbar = tqdm(
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"Loading {model_name} Language Model",
                )
            pbar.total = progress[1]
            p.max = progress[1]
            # slight hackiness to set the initial value if resuming a download or switching files
            if pbar.initial == 0 or pbar.initial > progress[0]:
                pbar.initial = progress[0]
            p.set(
                value=progress[0],
                message=f"Loading {model_name} Language Model: {humanize.naturalsize(progress[0], binary=True)}/{humanize.naturalsize(progress[1], binary=True)}",
            )
            pbar.n = progress[0]
            pbar.refresh()
    if pbar:
        pbar.close()
    print(f"{model_name} language model loaded.\n")
    ui.notification_show(f"{model_name} Language Model loaded")
