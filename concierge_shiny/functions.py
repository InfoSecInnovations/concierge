from shiny import ui
from concierge_backend_lib.ollama import load_model
from tqdm import tqdm
from isi_util.async_generator import asyncify_generator
import humanize
from concierge_backend_lib.authentication import get_username
from concierge_backend_lib.authorization import auth_enabled, has_scope
from auth import WebAppAsyncTokenTaskRunner


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
        return f"PDF File: {
            md_link(
                f'{doc_url(collection_name, page["type"], doc_metadata["id"])}#page={page_metadata["page"]}',
                f'page {page_metadata["page"]} of {doc_metadata["filename"]}',
            )
        }"
    if page["type"] == "web":
        return f"Web page: {md_link(page_metadata['source'])} scraped {doc_metadata['ingest_date']} from parent URL {md_link(doc_metadata['source'])}"
    if "filename" in doc_metadata:
        return f"{doc_metadata['extension']} file {
            md_link(
                doc_url(collection_name, doc_metadata['type'], doc_metadata['id']),
                doc_metadata['filename'],
            )
        }"
    return f"{doc_metadata['type']} type document from {doc_metadata['source']}"


def doc_link(collection_name, doc):
    if doc["type"] == "pdf":
        return f"PDF File: {
            md_link(doc_url(collection_name, doc['type'], doc['id']), doc['filename'])
        }"
    if doc["type"] == "web":
        return f"Web page: {md_link(doc['source'])}"
    if "filename" in doc:
        return f"{doc['extension'] if 'extension' in doc else doc['type']} file {
            md_link(doc_url(collection_name, doc['type'], doc['id']), doc['filename'])
        }"
    return f"{doc['type']} type document from {doc['source']}"


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


def format_collection_name(collection_data, user_info):
    if "type" not in collection_data or collection_data["type"] == "collection:shared":
        return collection_data["displayName"]
    user_id = user_info["sub"]
    if (
        "attributes" in collection_data
        and "concierge_owner" in collection_data["attributes"]
    ):
        if collection_data["attributes"]["concierge_owner"][0] == user_id:
            return f"{collection_data['displayName']} (private)"
        return f"{collection_data['displayName']} (private, belongs to {get_username(collection_data['attributes']['concierge_owner'][0])})"
    return f"{collection_data['displayName']} (private, owner unknown)"


async def has_edit_access(permissions, task_runner: WebAppAsyncTokenTaskRunner):
    if not auth_enabled():
        return True
    if permissions is None:  # this means we haven't loaded the permissions yet
        return False
    if (
        "collection:private:create" in permissions
        or "collection:shared:create" in permissions
    ):
        return True

    async def has_update(token):
        return await has_scope(token["access_token"], "update")

    async def has_delete(token):
        return await has_scope(token["access_token"], "delete")

    if await task_runner.run_async_task(has_update):
        return True
    if await task_runner.run_async_task(has_delete):
        return True
    return False


async def has_read_access(task_runner: WebAppAsyncTokenTaskRunner):
    if not auth_enabled():
        return True

    # TODO: how to determine that the user could read a collection if no collections have been created yet
    async def has_read(token):
        return await has_scope(token["access_token"], "read")

    return await task_runner.run_async_task(has_read)
