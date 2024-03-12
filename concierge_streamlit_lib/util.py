import streamlit as st

def cache_to_session_state(dict_name, item_name, func):
    if dict_name not in st.session_state:
        st.session_state[dict_name] = {}
    if item_name not in st.session_state[dict_name]:
        st.session_state[dict_name][item_name] = func()
    return st.session_state[dict_name][item_name]