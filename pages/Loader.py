import streamlit as st
from loader_functions import InitCollection, Insert
from loaders.pdf import LoadPDF
from pathlib import Path

# cached items

upload_dir = 'uploads'

@st.cache_resource
def CreateUploadDir():
    Path(upload_dir).mkdir(exist_ok=True)

@st.cache_resource
def GetCollection():
    return InitCollection("facts")

CreateUploadDir()
collection = GetCollection()

# mutable page display

# https://discuss.streamlit.io/t/are-there-any-ways-to-clear-file-uploader-values-without-using-streamlit-form/40903 see this hack for clearing the file uploader
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0

st.write('# Document Loader')

if "files" in st.session_state:
    st.write('Processing files...')
    for file in st.session_state["files"]:
            if file.type == 'application/pdf':
                print(file.name)
                with open(Path(upload_dir, file.name), "wb") as f:
                    f.write(file.getbuffer())
                pages = LoadPDF(upload_dir, file.name)
                Insert(pages, collection)
    del st.session_state["files"]
    st.rerun()

else:
    files = st.file_uploader(label='Select files to add to database', accept_multiple_files=True, key=st.session_state["file_uploader_key"])
    if files and len(files):
        if st.button(label='Ingest'):
            st.session_state["files"] = files
            st.session_state["file_uploader_key"] += 1
            st.rerun()
