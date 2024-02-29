import streamlit as st

def CollectionDropdown(no_collections_message = "You don't have any collections, please create one."):
    if not len(st.session_state["collections"]):
        st.write(no_collections_message)
        return False
    else:
        st.selectbox("Collection", st.session_state["collections"], key="selected_collection")
        return True