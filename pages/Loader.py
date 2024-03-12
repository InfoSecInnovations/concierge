import streamlit as st
from loaders.pdf import load_pdf
from loaders.web import load_web
from pathlib import Path
from stqdm import stqdm
from concierge_streamlit_lib.collections import ensure_collections, collection_dropdown, init_collection_cached, create_collection_widget, SELECTED_COLLECTION
from concierge_backend_lib.ingesting import insert
from concierge_streamlit_lib.status import sidebar_status

PROCESSING = "loader_processing"

# ---- first run only ----

upload_dir = 'uploads'

@st.cache_resource
def create_upload_dir():
    Path(upload_dir).mkdir(exist_ok=True)

create_upload_dir()
ensure_collections()

# https://discuss.streamlit.io/t/are-there-any-ways-to-clear-file-uploader-values-without-using-streamlit-form/40903 see this hack for clearing the file uploader
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0

if "input_urls" not in st.session_state:
    st.session_state["input_urls"] = []
    st.session_state["processing_urls"] = []

if PROCESSING not in st.session_state:
    st.session_state[PROCESSING] = False

# ---- main loop ----

def add_url():
    url = st.session_state[f'input_url_{len(st.session_state["input_urls"])}']
    if url:
        st.session_state["input_urls"].append(url)

def ingest():
    st.session_state[PROCESSING] = True
    st.session_state["processing_urls"] = st.session_state["input_urls"].copy()
    st.session_state["processing_files"] = st.session_state[st.session_state["file_uploader_key"]]
    st.session_state["input_urls"] = []
    st.session_state["file_uploader_key"] += 1

sidebar_status()

st.write('# Document Loader')
st.session_state["loader_container"] = st.empty()
st.session_state["input_container"] = st.empty()
if st.session_state[PROCESSING]:
    collection = init_collection_cached(st.session_state[SELECTED_COLLECTION])
    files = st.session_state["processing_files"]
    if files and len(files):
        with st.session_state["loader_container"].container():
            st.write('Processing files...')
            for file in files:
                if file.type == 'application/pdf':
                    print(file.name)
                    with open(Path(upload_dir, file.name), "wb") as f:
                        f.write(file.getbuffer())
                    pages = load_pdf(upload_dir, file.name)
                    page_progress = stqdm(total=len(pages), desc=f"Loading PDF {file.name}", backend=True)
                    for x in insert(pages, collection):
                        page_progress.n = x[0] + 1
                        page_progress.refresh()
                    page_progress.close()
        collection.flush()
        print('done loading files\n')

    if len(st.session_state["processing_urls"]):
        with st.session_state["loader_container"].container():
            st.write('Processing URLs...')
            for url in st.session_state["processing_urls"]:
                if not url:
                    continue
                print(url)
                pages = load_web(url)
                page_progress = stqdm(total=len(pages), desc=f"Loading URL {url}", backend=True)
                for x in insert(pages, collection):
                    page_progress.n = x[0] + 1
                    page_progress.refresh()
                page_progress.close()
        print('done loading URLs\n')
        st.session_state["processing_urls"] = []
    st.session_state[PROCESSING] = False
    st.rerun()
else:
    with st.session_state["input_container"].container():
        collections_exist = collection_dropdown()
        create_collection_widget()
        if collections_exist:
            st.file_uploader(label='Select files to add to database', accept_multiple_files=True, key=st.session_state["file_uploader_key"], disabled=st.session_state[PROCESSING])
            st.write('### URLs ###')
            for index, url in enumerate(st.session_state["input_urls"]):
                st.session_state["input_urls"][index] = st.text_input("URL", url, label_visibility="collapsed", key=f"input_url_{index}", disabled=st.session_state[PROCESSING])
            st.text_input("URL", "", label_visibility="collapsed", key=f'input_url_{len(st.session_state["input_urls"])}', on_change=add_url, disabled=st.session_state[PROCESSING])
            st.button(label='Ingest', on_click=ingest, disabled=st.session_state[PROCESSING])
