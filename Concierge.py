import streamlit as st
from streamlit_option_menu import option_menu
from concierge_streamlit_lib.add_api_handler import add_api_handler
from concierge_streamlit_lib.status import sidebar_status
from concierge_streamlit_lib.collections import ensure_collections
from tornado.web import StaticFileHandler
from concierge_streamlit_pages.home import home
from concierge_streamlit_pages.loader import loader
from concierge_streamlit_pages.prompter import prompter
from concierge_streamlit_pages.collection_management import collection_management

st.set_page_config(
    page_title="Concierge",
    page_icon="👋",
)

add_api_handler(r"/uploads/(.*)", StaticFileHandler, {"path": "uploads"})
ensure_collections()

with st.sidebar:
    option_menu(
        menu_title=None,
        options=["Concierge", "Loader", "Prompter", "Collection Management"],
        key="selected_page"
    )

sidebar_status()

if st.session_state["selected_page"] == "Concierge":
    home()
elif st.session_state["selected_page"] == "Loader":
    loader()
elif st.session_state["selected_page"] == "Prompter":
    prompter()
elif st.session_state["selected_page"] == "Collection Management":
    collection_management()

