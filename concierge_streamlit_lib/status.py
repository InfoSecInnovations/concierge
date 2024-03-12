import streamlit as st
import requests
from concierge_backend_lib.collections import get_collections
from pymilvus.exceptions import MilvusException

@st.cache_data(ttl="10s")
def get_status():
    try:
        ollama_up = requests.get("http://localhost:11434/").status_code == 200
    except:
        ollama_up = False

    try:
        get_collections()
        milvus_up = True
    except MilvusException:
        milvus_up = False

    return {
        "ollama": ollama_up,
        "milvus": milvus_up
    }

def sidebar_status():
    status = get_status()
    if status["ollama"]:
        st.sidebar.success("Ollama is up and running", icon="🟢")
    else:
        st.sidebar.error("Ollama server not found, please ensure the ollama Docker container is running! If so you may have to take down the docker compose and put it up again", icon="🔴")
    if status["milvus"]:
        st.sidebar.success("Milvus is up and running", icon="🟢")
    else:
        st.sidebar.error("Milvus database not found, please ensure the milvus-standalone, etcd and minio Docker containers are running! If so you may have to take down the docker compose and put it up again", icon="🔴")
