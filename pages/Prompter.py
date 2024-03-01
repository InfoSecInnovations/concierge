import streamlit as st
import os
from stqdm import stqdm
from configobj import ConfigObj
from pathlib import Path
from concierge_backend_lib.prompting import LoadModel, GetContext, GetResponse
from concierge_streamlit_lib.collections import CollectionDropdown, EnsureCollections, GetExistingCollectionCached, SELECTED_COLLECTION

PROCESSING = "prompter_processing"

# ---- first run only ----

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
    print("Language model loaded.\n")

LoadLLMModel()
EnsureCollections()

reference_limit = 5
tasks = LoadConfig('tasks')
personas = LoadConfig('personas')
enhancers = LoadConfig('enhancers')
default_task_index = 0 if 'question' not in tasks else list(tasks.keys()).index('question')

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if PROCESSING not in st.session_state:
    st.session_state[PROCESSING] = False

# ---- main loop ----

def on_input():
    st.session_state[PROCESSING] = True

st.write('# Query your data')
with st.container():
    message_container = st.container()
    for message in st.session_state["messages"]:
        with message_container.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.markdown(message["content"])
            else:
                st.write(message["content"])
    if CollectionDropdown(no_collections_message="You don't have any collections. Please go to the Loader page, create a collection and ingest some data into it.", disabled=st.session_state[PROCESSING]):
        col1, col2, col3 = st.columns(3)
        task = col1.selectbox('Task', tasks.keys(), index=default_task_index, disabled=st.session_state[PROCESSING])
        persona = col2.selectbox('Persona', ['None', *personas.keys()], disabled=st.session_state[PROCESSING])
        selected_enhancers = col3.multiselect('Enhancers', enhancers.keys(), disabled=st.session_state[PROCESSING])
        source_file = st.file_uploader("Source File (optional)", disabled=st.session_state[PROCESSING])
        user_input = st.chat_input(tasks[task]["greeting"], disabled=st.session_state[PROCESSING], on_submit=on_input)
        if user_input:
            full_message = f'Task: {task}'
            if persona and persona != 'None':
                full_message += f', Persona: {persona}'
            if selected_enhancers and len(selected_enhancers):
                full_message += f', Enhancers: {selected_enhancers}'
            full_message += f'.\n\nCollection: {st.session_state[SELECTED_COLLECTION]}'
            full_message += f'\n\nInput: {user_input}'
            print(full_message)
            print('\n')
            st.session_state["messages"].append({"role": "user", "content": full_message})
            with message_container.chat_message("user"):
                st.write(full_message)
            with message_container.chat_message("assistant"):
                context = GetContext(GetExistingCollectionCached(st.session_state[SELECTED_COLLECTION]), reference_limit, user_input)

                def stream_message():
                    yield 'Responding based on the following sources:\n\n'
                    print('Responding based on the following sources:')
                    for source in context["sources"]:
                        metadata = source["metadata"]
                        if source["type"] == "pdf":
                            print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]}')
                            yield f'   PDF File: [page {metadata["page"]} of {metadata["filename"]}](<uploads/{metadata["filename"]}#page={metadata["page"]}>)\n\n'
                        if source["type"] == "web":
                            print(f'   Web page: {metadata["source"]} scraped {metadata["ingest_date"]}')
                            yield f'   Web page: {metadata["source"]} scraped {metadata["ingest_date"]}\n\n'              
                    if "prompt" in tasks[task]:
                        yield GetResponse(
                            context["context"], 
                            tasks[task]["prompt"], 
                            user_input,
                            None if not persona or persona == 'None' else personas[persona]["prompt"],
                            None if not selected_enhancers else [enhancers[enhancer]["prompt"] for enhancer in selected_enhancers],
                            None if not source_file else source_file.getvalue().decode()
                        )

                full_response = st.write_stream(stream_message)
                print(full_response)
                print('\n')
                st.session_state["messages"].append({"role": "assistant", "content": full_response})
                st.session_state[PROCESSING] = False
                st.rerun()