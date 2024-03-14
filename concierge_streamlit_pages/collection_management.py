import streamlit as st
from concierge_streamlit_lib.collections import get_existing_collection_cached, create_collection_widget, drop_collection, COLLECTIONS

def collection_management():

    st.write('# Collections Manager')
    create_collection_widget()

    for collection_name in st.session_state[COLLECTIONS]:
        collection = get_existing_collection_cached(collection_name)
        with st.container(border=1):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"### My collection: {collection_name}")
                # TODO need to better handle description. will be really nice for user experience.
                #st.text_area("Detailed description", this_collection.description)
                st.write("Entity count: ", collection.num_entities)
            with col2:
                st.button("delete collection", key=f"delete_{collection_name}", on_click=drop_collection, args=[collection_name])