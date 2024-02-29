import streamlit as st
from concierge_backend_lib.collections import GetCollections, InitCollection, GetExistingCollection
from concierge_streamlit_lib.util import CacheToSessionState

@st.cache_resource
def GetCollectionsCached():
    return GetCollections()

def EnsureCollections():
    if "collections" not in st.session_state:
        st.session_state["collections"] = GetCollectionsCached()

def InitCollectionCached(collection_name):
    return CacheToSessionState("initialized_collections", collection_name, lambda: InitCollection(collection_name))

def GetExistingCollectionCached(collection_name):
    return CacheToSessionState("existing_collections", collection_name, lambda: GetExistingCollection(collection_name))

def CollectionDropdown(no_collections_message = "You don't have any collections, please create one."):
    if not len(st.session_state["collections"]):
        st.write(no_collections_message)
        return False
    else:
        st.selectbox("Collection", st.session_state["collections"], key="selected_collection")
        return True
    
def CreateCollectionWidget():
    with st.form(key="new_collection_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        new_collection_name = col1.text_input(label="New Collection", label_visibility="collapsed")
        if col2.form_submit_button(label="Create Collection"):
            if new_collection_name:
                InitCollectionCached(new_collection_name)
                st.session_state["collections"].append(new_collection_name)
                st.rerun()