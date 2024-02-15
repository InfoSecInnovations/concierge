import streamlit as st
import os
from stqdm import stqdm
from configobj import ConfigObj
from pathlib import Path
from prompter_functions import LoadModel, InitCollection, GetContext, GetResponse

@st.cache_data
def LoadConfig(dir):
    files = os.listdir(Path('prompter_config', dir).as_posix())
    return { file.replace('.concierge', ''): ConfigObj(
        Path('prompter_config', dir, file).as_posix(), list_values=False
    ) for file in filter(lambda file: file.endswith('.concierge'), files)} 

@st.cache_resource
def LoadLLMModel():
    pbar = None
    for progress in LoadModel():
        if not pbar:
            pbar = stqdm(
                unit="B",
                unit_scale=True,
                unit_divisor=1024, 
                backend=True,
                desc="Loading Language Model"
            )
        # slight hackiness to set the initial value if resuming a download or switching files
        if pbar.initial == 0 or pbar.initial > progress[0]:
            pbar.initial = progress[0]
        pbar.total = progress[1]
        pbar.n = progress[0]
        pbar.refresh()
    if pbar:
        pbar.close()

@st.cache_resource
def GetCollection():
    return InitCollection()

reference_limit = 5
tasks = LoadConfig('tasks')
personas = LoadConfig('personas')
enhancers = LoadConfig('enhancers')

collection = GetCollection()

if "messages" not in st.session_state:
    st.session_state["messages"] = []

st.write('# Query your data')
col1, col2, col3 = st.columns(3)
task = col1.selectbox('Task', tasks.keys())
persona = col2.selectbox('Persona', ['None', *personas.keys()])
enhancers = col3.multiselect('Enhancers', enhancers.keys())
source_file = st.file_uploader("Source File (optional)")
with st.container():
    message_container = st.container()
    for message in st.session_state["messages"]:
        with message_container.chat_message(message["role"]):
            st.write(message["content"])
    user_input = st.chat_input(tasks[task]["greeting"])
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with message_container.chat_message("user"):
            st.write(user_input)
        with message_container.chat_message("assistant"):
            context = GetContext(collection, reference_limit, user_input)
            st.write('Responding based on the following sources:')
            print('\nResponding based on the following sources:')
            for source in context["sources"]:
                metadata = source["metadata"]
                if source["type"] == "pdf":
                    print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]} located at {metadata["path"]}')
                    st.write(f'   PDF File: page {metadata["page"]} of {metadata["filename"]} located at {metadata["path"]}')
                if source["type"] == "web":
                    print(f'   Web page: {metadata["source"]} scraped {metadata["ingest_date"]}')
                    st.write(f'   Web page: {metadata["source"]} scraped {metadata["ingest_date"]}')
            
            if "prompt" in tasks[task]:
                response = GetResponse(
                    context["context"], 
                    tasks[task]["prompt"], 
                    user_input,
                    None if not persona or persona == 'None' else personas[persona]["prompt"],
                    None if not enhancers else [enhancers[enhancer]["prompt"] for enhancer in enhancers],
                    None if not source_file else source_file.getvalue().decode()
                )

                print(response)
                st.markdown(response)