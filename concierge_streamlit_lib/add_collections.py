import streamlit as st
from loader_functions import GetCollections

@st.cache_resource
def GetCollectionList():
    return GetCollections()

def EnsureCollections():
    if "collections" not in st.session_state:
        st.session_state["collections"] = GetCollectionList()