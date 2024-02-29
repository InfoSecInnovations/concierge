import streamlit as st
#from stqdm import stqdm
#from configobj import ConfigObj
#from pathlib import Path
#from prompter_functions import LoadModel, InitCollection, GetContext, GetResponse

from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)

# delete collection
def delete_collection():
    print("foo")

# delete document
def delete_document():
    print("foo")

# TODO would a delete entity be a "thing"?

# ---- first run only ----

# TODO does this need to use a loop function?

# TODO when loader or prompter have been run, there's a connection... stop this connection?

# TODO will need to eventually allow other connections
connections.connect("default", host="localhost", port="19530")

collections = utility.list_collections(timeout=None, using='default')


#if "messages" not in st.session_state:
#    st.session_state["messages"] = []

#if "processing" not in st.session_state:
#    st.session_state["processing"] = False

# ---- main loop ----


### TODO use for rename?
#schema = CollectionSchema(fields=[
#...     FieldSchema("int64", DataType.INT64, description="int64", is_primary=True),
#...     FieldSchema("float_vector", DataType.FLOAT_VECTOR, is_primary=False, dim=128),
#... ])
#collection = Collection(name="old_collection", schema=schema)
#utility.rename_collection("old_collection", "new_collection") # Output: True
#utility.drop_collection("new_collection")
#utility.has_collection("new_collection") # Output: False


def on_input():
    st.session_state["processing"] = True

st.write('# Collections Manager')



for collection in collections:

    # enumerate documents in collection
    # TODO consider variable rename for readability. not a fan of case being so important.
    this_collection = Collection(collection)
    this_collection.load()

    # TODO need to think query approach consider refactoring
    # grab all entities regarless of metadata_type.
    #response = this_collection.query(
    #    expr = "",
    #    limit = this_collection.num_entities,
    #    output_fields=["metadata_type", "metadata"],
    #)

    # maybe this?
    response = this_collection.query(
        expr = 'metadata_type == "pdf"',
        output_fields=["metadata"],
    )

    for entity in response:
        metadata = entity["metadata"]

        # works!
        #st.write(entity)
        st.write(metadata)

        # trail of woe
        #print(-f'{metadata["filename"]}')
        #st.write({metadata["filename"]})
        #st.write([{metadata["filename"]}])
        #st.write('PDF File: page {metadata["page"]} of {metadata["filename"]}')
        #yield f'   PDF File: [page {metadata["page"]} of {metadata["filename"]}](<uploads/{metadata["filename"]}#page={metadata["page"]}>)\n\n'
        #print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]}')


    with st.container(border=1):
        col1, col2 = st.columns(2)
        with col1:
            st.write("### My collection:")
            # TODO future for when we support additional collections
            #st.write("### " + collection + " Collection")
            # TODO need to better handle description. will be really nice for user experience.
            #st.text_area("Detailed description", this_collection.description)
            st.write("Entity count: ", this_collection.num_entities)

        with col2:
            st.button("delete collection")

        with st.expander("See documents in this collection:"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("foo")

            with col_b:
                st.button("delete document")


#with st.container():
#    message_container = st.container()
#    for message in st.session_state["messages"]:
#        with message_container.chat_message(message["role"]):
#            if message["role"] == "assistant":
#                st.markdown(message["content"])
#            else:
#                st.write(message["content"])
#    col1, col2, col3 = st.columns(3)
#    task = col1.selectbox('Task', tasks.keys(), index=default_task_index)
#    persona = col2.selectbox('Persona', ['None', *personas.keys()])
#    selected_enhancers = col3.multiselect('Enhancers', enhancers.keys())
#    source_file = st.file_uploader("Source File (optional)", disabled=st.session_state["processing"])
#    user_input = st.chat_input(tasks[task]["greeting"], disabled=st.session_state["processing"], on_submit=on_input)
#    if user_input:
#        full_message = f'Task: {task}'
#        if persona and persona != 'None':
#            full_message += f', Persona: {persona}'
#        if selected_enhancers and len(selected_enhancers):
#            full_message += f', Enhancers: {selected_enhancers}'
#        full_message += f'.\n\nInput: {user_input}'
#        print(full_message)
#        print('\n')
#        st.session_state["messages"].append({"role": "user", "content": full_message})
#        with message_container.chat_message("user"):
#            st.write(full_message)
#        with message_container.chat_message("assistant"):
#            context = GetContext(collection, reference_limit, user_input)

#            def stream_message():
#                yield 'Responding based on the following sources:\n\n'
#                print('Responding based on the following sources:')
#                for source in context["sources"]:
#                    metadata = source["metadata"]
#                    if source["type"] == "pdf":
#                        print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]}')
#                        yield f'   PDF File: [page {metadata["page"]} of {metadata["filename"]}](<uploads/{metadata["filename"]}#page={metadata["page"]}>)\n\n'
#                    if source["type"] == "web":
#                        print(f'   Web page: {metadata["source"]} scraped {metadata["ingest_date"]}')
#                        yield f'   Web page: {metadata["source"]} scraped {metadata["ingest_date"]}\n\n'              
#                if "prompt" in tasks[task]:
#                    yield GetResponse(
#                        context["context"], 
#                        tasks[task]["prompt"], 
#                        user_input,
#                        None if not persona or persona == 'None' else personas[persona]["prompt"],
#                        None if not selected_enhancers else [enhancers[enhancer]["prompt"] for enhancer in selected_enhancers],
#                        None if not source_file else source_file.getvalue().decode()
#                    )

#            full_response = st.write_stream(stream_message)
#            print(full_response)
#            print('\n')
#            st.session_state["messages"].append({"role": "assistant", "content": full_response})
#            st.session_state["processing"] = False
#            st.rerun()
