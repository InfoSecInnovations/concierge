import streamlit as st
from concierge_streamlit_lib.collections import EnsureCollections, GetExistingCollectionCached, CreateCollectionWidget, DropCollection

# ---- first run only ----

EnsureCollections()

# ---- main loop ----

st.write('# Collections Manager')

CreateCollectionWidget()

for collection_name in st.session_state["collections"]:
    collection = GetExistingCollectionCached(collection_name)

    with st.container(border=1):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"### My collection: {collection_name}")
            # TODO need to better handle description. will be really nice for user experience.
            #st.text_area("Detailed description", this_collection.description)
            st.write("Entity count: ", collection.num_entities)

        with col2:
            st.button("delete collection", key=f"delete_{collection_name}", on_click=DropCollection, args=[collection_name])