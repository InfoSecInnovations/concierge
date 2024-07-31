from shiny import ui, module
from markdown_renderer import md


@module.ui
def home_ui():
    return ui.markdown(
        """

        # Data Concierge AI

        AI should be simple, safe, and amazing.

        Concierge is an open-source AI framework built specifically for
        how you use data.

        ### Getting started:  
        1. Create a collection with Collection Management  
        2. Load PDF or web data into the collection with the Loader  
        3. Use Prompter to work with Concierge.


        ### Tips for getting the most out of Concierge:
        - You can have as many collections as you want. Organize your data how you'd like!
        - Experiment with the selection options in Prompter. You can have Concierge help you with lots of tasks.
        - If you have any problems, reach out to us via github issues or the contact page on <https://dataconcierge.ai>{target="_blank"}


        ### Are you a dev? Want to get even more involved?
        - Create a task file to extend Concierge's capabilities
        - Add enhancer files to have parting thoughts
        - Build a loader to allow new data in Concierge
        - Review our github issues, we would love your input
    """,
        render_func=md.render,
    )
