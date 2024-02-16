import streamlit as st
from add_api_handler import AddApiHandler
from tornado.web import StaticFileHandler

st.set_page_config(
    page_title="Concierge",
    page_icon="👋",
)

AddApiHandler(r"/uploads/(.*)", StaticFileHandler, {"path": "uploads"})

st.write("# Welcome to Concierge!")

st.sidebar.success("Please pick a mode above.")

st.markdown(
    """
    Concierge is an open-source AI suite built specifically for
    how you use data.

    **Select a mode from the sidebar** to see some examples
    of what Concierge can do!

    ### Want to learn more?
    - Check out the quick start documentation
    - Learn more with the detailed online documentation.
    - Ask a question in our community forums
    - Read the Concierge manifesto to learn more about why this project is different

    ### Want to get involved?
    - Create a task file to extend Concierge's capabilities
    - Add enhancer files to have parting thoughts
    - build a loader to allow new data in Concierge
    - Check the Dev Readme to see the quickest on ramps
    - review our github issues where we're needing input
"""
)