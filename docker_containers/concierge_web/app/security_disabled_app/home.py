from shiny import ui, Inputs, Outputs, Session, render, module, reactive
from ..common.markdown_renderer import md

title = """
# Data Concierge AI

AI should be simple, safe, and amazing.

Concierge is an open-source AI framework built specifically for
how you use data.
"""

quickstart = """
### Getting started:  
1. Create a collection with Collection Management.  
2. Load documents (currently PDF and text files are supported) and/or web data into the collection. 
3. Use Prompter to work with Concierge.
"""

tips = """
### Tips for getting the most out of Concierge:
- You can have as many collections as you want. Organize your data how you'd like!
- Experiment with the selection options in Prompter. You can have Concierge help you with lots of tasks.
- If you have any problems, reach out to us via github issues or the contact page on <https://dataconcierge.ai>{target="_blank"}
"""

contributing = """
### Are you a dev? Want to get even more involved?
- Create a task file to extend Concierge's capabilities
- Add enhancer files to have parting thoughts
- Build a loader to allow new data in Concierge
- Review our github issues, we would love your input
"""


@module.ui
def home_ui():
    return ui.output_ui("home_text")


@module.server
def home_server(
    input: Inputs,
    output: Outputs,
    session: Session
):

    @render.ui
    def home_text():
        return ui.markdown("\n".join([title, quickstart, tips, contributing]), render_func=md.render)
