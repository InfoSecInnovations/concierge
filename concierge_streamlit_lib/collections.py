import streamlit as st
from concierge_backend_lib.collections import GetCollections, InitCollection, GetExistingCollection
from concierge_streamlit_lib.util import CacheToSessionState
from pymilvus import utility

INITIALIZED_COLLECTIONS = "initialized_collections"
EXISTING_COLLECTIONS = "existing_collections"
COLLECTIONS = "collections"
SELECTED_COLLECTION = "selected_collection"

@st.cache_resource
def GetCollectionsCached():
    return GetCollections()

def EnsureCollections():
    if COLLECTIONS not in st.session_state:
        st.session_state[COLLECTIONS] = GetCollectionsCached()

def InitCollectionCached(collection_name):
    return CacheToSessionState(INITIALIZED_COLLECTIONS, collection_name, lambda: InitCollection(collection_name))

def GetExistingCollectionCached(collection_name):
    return CacheToSessionState(EXISTING_COLLECTIONS, collection_name, lambda: GetExistingCollection(collection_name))

def CollectionDropdown(no_collections_message = "You don't have any collections, please create one.", disabled = False):
    if not len(st.session_state[COLLECTIONS]):
        st.write(no_collections_message)
        return False
    else:
        st.selectbox("Collection", st.session_state[COLLECTIONS], key=SELECTED_COLLECTION, disabled=disabled)
        return True
    
def CreateCollectionWidget():
    with st.form(key="new_collection_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        new_collection_name = col1.text_input(label="New Collection", label_visibility="collapsed")
        if col2.form_submit_button(label="Create Collection"):
            if new_collection_name:
                InitCollectionCached(new_collection_name)
                st.session_state[COLLECTIONS].append(new_collection_name)
                st.rerun()

def DropCollection(collection_name):
    if INITIALIZED_COLLECTIONS in st.session_state:
        del st.session_state[INITIALIZED_COLLECTIONS][collection_name]
    if EXISTING_COLLECTIONS in st.session_state:
        del st.session_state[EXISTING_COLLECTIONS][collection_name]
    if COLLECTIONS in st.session_state:
        st.session_state[COLLECTIONS].remove(collection_name)
    utility.drop_collection(collection_name)