import streamlit as st
from loader_functions import InitCollection
from prompter_functions import InitCollection as InitCollectionRead

@st.cache_data
def GetCollectionForWriting(collection_name):
    return InitCollection(collection_name)

@st.cache_data
def GetCollectionForReading(collection_name):
    return InitCollectionRead(collection_name)