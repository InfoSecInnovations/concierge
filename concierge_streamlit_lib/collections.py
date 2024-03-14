import streamlit as st
from concierge_backend_lib.collections import get_collections, init_collection, get_existing_collection
from concierge_streamlit_lib.util import cache_to_session_state
from pymilvus import utility

INITIALIZED_COLLECTIONS = "initialized_collections"
EXISTING_COLLECTIONS = "existing_collections"
COLLECTIONS = "collections"
SELECTED_COLLECTION = "selected_collection"

@st.cache_resource
def get_collections_cached():
    return get_collections()

def ensure_collections():
    if COLLECTIONS not in st.session_state:
        st.session_state[COLLECTIONS] = get_collections_cached()

def init_collection_cached(collection_name):
    return cache_to_session_state(INITIALIZED_COLLECTIONS, collection_name, lambda: init_collection(collection_name))

def get_existing_collection_cached(collection_name):
    return cache_to_session_state(EXISTING_COLLECTIONS, collection_name, lambda: get_existing_collection(collection_name))

def set_selected_collection():
    st.session_state[SELECTED_COLLECTION]=st.session_state["_selected_collection"] 

def collection_dropdown(no_collections_message = "You don't have any collections, please create one.", disabled = False):
    if not len(st.session_state[COLLECTIONS]):
        st.write(no_collections_message)
        return False
    else:
        index = 0 if SELECTED_COLLECTION not in st.session_state else st.session_state[COLLECTIONS].index(st.session_state[SELECTED_COLLECTION])
        st.selectbox("Collection", st.session_state[COLLECTIONS], key="_selected_collection", on_change=set_selected_collection, disabled=disabled, index=index)
        return True
    
def create_collection_widget():
    with st.form(key="new_collection_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        new_collection_name = col1.text_input(label="New Collection", label_visibility="collapsed")
        st.write("Hint: Collection names must contain only letters, numbers, or underscores.")
        if col2.form_submit_button(label="Create Collection"):
            if new_collection_name:
                init_collection_cached(new_collection_name)
                st.session_state[COLLECTIONS].append(new_collection_name)
                st.rerun()

def drop_collection(collection_name):
    if INITIALIZED_COLLECTIONS in st.session_state:
        del st.session_state[INITIALIZED_COLLECTIONS][collection_name]
    if EXISTING_COLLECTIONS in st.session_state:
        del st.session_state[EXISTING_COLLECTIONS][collection_name]
    if COLLECTIONS in st.session_state:
        st.session_state[COLLECTIONS].remove(collection_name)
    utility.drop_collection(collection_name)
