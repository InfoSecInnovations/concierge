import streamlit as st
from pathlib import Path
from concierge_streamlit_lib.collections import collection_dropdown, create_collection_widget
from concierge_streamlit_lib.status import LOADER_PROCESSING, UPLOAD_DIR

@st.cache_resource
def create_upload_dir():
    Path(UPLOAD_DIR).mkdir(exist_ok=True)

def add_url():
    url = st.session_state[f'input_url_{len(st.session_state["input_urls"])}']
    if url:
        st.session_state["input_urls"].append(url)

def ingest():
    st.session_state[LOADER_PROCESSING] = True
    st.session_state["processing_urls"] = st.session_state["input_urls"].copy()
    st.session_state["processing_files"] = st.session_state[st.session_state["file_uploader_key"]]
    st.session_state["input_urls"] = []
    st.session_state["file_uploader_key"] += 1

def loader():

    create_upload_dir()

    # https://discuss.streamlit.io/t/are-there-any-ways-to-clear-file-uploader-values-without-using-streamlit-form/40903 see this hack for clearing the file uploader
    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 0

    st.write('# Document Loader')
    with st.empty().container():
        if not st.session_state[LOADER_PROCESSING]:
            collections_exist = collection_dropdown()
            create_collection_widget()
            if collections_exist:
                st.file_uploader(label='Select files to add to database', accept_multiple_files=True, key=st.session_state["file_uploader_key"], disabled=st.session_state[LOADER_PROCESSING])
                st.write('### URLs ###')
                for index, url in enumerate(st.session_state["input_urls"]):
                    st.session_state["input_urls"][index] = st.text_input("URL", url, label_visibility="collapsed", key=f"input_url_{index}", disabled=st.session_state[LOADER_PROCESSING])
                st.text_input("URL", "", label_visibility="collapsed", key=f'input_url_{len(st.session_state["input_urls"])}', on_change=add_url, disabled=st.session_state[LOADER_PROCESSING])
                if st.button(label='Ingest', on_click=ingest, disabled=st.session_state[LOADER_PROCESSING]):
                    st.rerun()
