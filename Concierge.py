import streamlit as st
from concierge_streamlit_lib.add_api_handler import add_api_handler
from concierge_streamlit_lib.status import sidebar_status
from tornado.web import StaticFileHandler

st.set_page_config(
    page_title="Concierge",
    page_icon="👋",
)

add_api_handler(r"/uploads/(.*)", StaticFileHandler, {"path": "uploads"})

sidebar_status()

st.write("# Welcome to Concierge!")

st.markdown(
    """

    Data Concierge AI:
    AI should be simple, safe, and amazing.

    Concierge is an open-source AI framework built specifically for
    how you use data.

    #### Getting started:  
    1. Create a collecion with Collection Manager  
    2. Load PDF or web data into the collection with the Loader  
    3. Use Prompter to work with Concierge.


    #### Tips for getting the most out of Concierge:
    - You can have as many collections as you want. Organize your data how you'd like!
    - Experiment with the selection options in Prompter. You can have Concierge help you with lots of tasks.
    - If you have any problems, reach out to us via github issues or the contact page on https://dataconcierge.ai


    #### Are you a dev? Want to get even more involved?
    - Create a task file to extend Concierge's capabilities
    - Add enhancer files to have parting thoughts
    - Build a loader to allow new data in Concierge
    - Review our github issues, we would love your input
"""
)
