from shiny import ui
from concierge_backend_lib.ollama import load_model
from tqdm import tqdm
from isi_util.async_generator import asyncify_generator
from shiny import render
from concierge_backend_lib.opensearch import get_client
from oid_configs import oauth_configs, oauth_config_data
import json
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError
import os
import dotenv

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
scope = ["openid profile email offline_access"]


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
                message=f"Loading {model_name} Language Model: {progress[0]}/{progress[1]}",
            )
            pbar.n = progress[0]
            pbar.refresh()
    if pbar:
        pbar.close()
    print(f"{model_name} language model loaded.\n")
    ui.notification_show(f"{model_name} Language Model loaded")


def get_authorized_client(session):
    if (
        "concierge_token_chunk_count" not in session.http_conn.cookies
        or "concierge_auth_provider" not in session.http_conn.cookies
    ):
        urls = []
        redirect_uri = f"{session.http_conn.headers["origin"]}/callback/"

        for provider, data in oauth_config_data.items():
            config = oauth_configs[provider]
            oauth = OAuth2Session(
                client_id=os.getenv(data["id_env_var"]),
                redirect_uri=redirect_uri + provider,
                scope=scope,
            )
            authorization_url, state = oauth.authorization_url(
                config["authorization_endpoint"]
            )
            urls.append(authorization_url)

        @render.ui
        def concierge_main():
            return ui.markdown("\n\n".join([f"<{url}>" for url in urls]))

        return (None, None)

    # TODO: only do this if security is enabled

    chunk_count = int(session.http_conn.cookies["concierge_token_chunk_count"])
    token = ""
    for i in range(chunk_count):
        token += session.http_conn.cookies[f"concierge_auth_{i}"]
    provider = session.http_conn.cookies["concierge_auth_provider"]
    oidc_config = oauth_configs[provider]
    data = oauth_config_data[provider]
    parsed_token = json.loads(token)
    oauth = OAuth2Session(client_id=os.getenv(data["id_env_var"]), token=parsed_token)
    try:
        oauth.get(
            oidc_config["userinfo_endpoint"]
        ).json()  # TODO: maybe do something with the user info?
    except TokenExpiredError:

        @render.ui
        def concierge_main():
            return ui.tags.script(f'window.location.href = "/refresh/{provider}"')

        return (None, None)

    return (get_client(parsed_token["id_token"]), parsed_token["id_token"])

    # TODO: if security isn't enabled make basic get_client call
