import ntpath
from shiny import ui
from concierge_backend_lib.ollama import load_model
from tqdm import tqdm
from util.async_generator import asyncify_generator


def chunk_link(uploads_dir, chunk):
    metadata = chunk["metadata"]
    if chunk["type"] == "pdf":
        return f'PDF File: [page {metadata["page"]} of {metadata["filename"]}](<{uploads_dir}/{metadata["filename"]}#page={metadata["page"]}>){{target="_blank"}}'
    if chunk["type"] == "web":
        return f'Web page: <{metadata["source"]}>{{target="_blank"}} scraped {metadata["ingest_date"]}'


def doc_link(uploads_dir, doc):
    if doc["type"] == "pdf":
        filename = ntpath.basename(doc["source"])
        return f'PDF File: [{filename}](<{uploads_dir}/{filename}>){{target="_blank"}}'
    if doc["type"] == "web":
        return f'Web page: <{doc["source"]}>{{target="_blank"}}'


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
                message=f"Loading {model_name} Language Model: {progress[0]}/{progress[1]}",
            )
            pbar.n = progress[0]
            pbar.refresh()
    if pbar:
        pbar.close()
    print(f"{model_name} language model loaded.\n")
    ui.notification_show(f"{model_name} Language Model loaded")
