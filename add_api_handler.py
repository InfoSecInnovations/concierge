from tornado.web import Application
from tornado.routing import Rule, PathMatches
import gc
import streamlit as st

@st.cache_data()
def AddApiHandler(uri, handler, kwargs = None):
    print("Setup Tornado. Should be called only once per handler")

    if "tornado" not in st.session_state:
        # Get instance of Tornado
        st.session_state["tornado"] = next(o for o in gc.get_referrers(Application) if o.__class__ is Application)

    # Setup custom handler
    st.session_state["tornado"].wildcard_router.rules.insert(0, Rule(PathMatches(uri), handler, kwargs))