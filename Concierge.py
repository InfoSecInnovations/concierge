import streamlit as st
from concierge_streamlit_lib.add_api_handler import AddApiHandler
from concierge_streamlit_lib.status import SidebarStatus
from tornado.web import StaticFileHandler

st.set_page_config(
    page_title="Concierge",
    page_icon="👋",
)

AddApiHandler(r"/uploads/(.*)", StaticFileHandler, {"path": "uploads"})

SidebarStatus()

st.write("# Welcome to Concierge!")

st.markdown(
    """

    Data Concierge AI:
    AI should be simple, safe, and amazing.

    Concierge is an open-source AI framework built specifically for
    how you use data.

    **Select a mode from the sidebar** to get started with
    Concierge.  Have fun!


    #### Are you a dev? Want to get even more involved?
    - Create a task file to extend Concierge's capabilities
    - Add enhancer files to have parting thoughts
    - Build a loader to allow new data in Concierge
    - Review our github issues, we would love your input
"""
)
