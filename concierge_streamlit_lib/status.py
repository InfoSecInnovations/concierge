import streamlit as st
from concierge_backend_lib.status import get_status

@st.cache_data(ttl="10s")
def get_status_cached():
    return get_status()

def sidebar_status():
    status = get_status_cached()
    if status["ollama"]:
        st.sidebar.success("Ollama is up and running", icon="🟢")
    else:
        st.sidebar.error("Ollama server not found, please ensure the ollama Docker container is running! If so you may have to take down the docker compose and put it up again", icon="🔴")
    if status["milvus"]:
        st.sidebar.success("Milvus is up and running", icon="🟢")
    else:
        st.sidebar.error("Milvus database not found, please ensure the milvus-standalone, etcd and minio Docker containers are running! If so you may have to take down the docker compose and put it up again", icon="🔴")
