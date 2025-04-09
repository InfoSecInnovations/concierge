from shiny import ui, Inputs, Outputs, Session, render, module, reactive
from concierge_util import auth_enabled
from .common.markdown_renderer import md
from .functions import has_edit_access, has_read_access

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

quickstart_readonly = """
### Getting started:

Just open the Prompter page, select a collection and ask away!

If there are no collections present you will need to ask someone with write access to create one, or obtain the permission to do so yourself.
"""

quickstart_no_access = """
### Getting started:

You currently don't have permission to do anything in Concierge, please contact an administrator to be assigned the correct roles!
"""

admin_tips = """
### Admin tips
- You can configure Keycloak to support many different login methods including OAuth and LDAP.
- Use the Keycloak administration UI to assign roles to users. Open up the Concierge realm and assign roles from the concierge-auth client.
- Once a collection has been created you can assign custom permissions to access it if you need something more granular than the provided roles.
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
    session: Session,
    permissions,
    user_info,
    task_runner,
):
    read_access = reactive.value(False)
    edit_access = reactive.value(False)

    @reactive.extended_task
    async def get_read_access():
        return await has_read_access(task_runner)

    @reactive.extended_task
    async def get_edit_access(permissions):
        return await has_edit_access(permissions, task_runner)

    @reactive.effect
    def on_get_read_access():
        read_access.set(get_read_access.result())

    @reactive.effect
    def on_get_edit_access():
        edit_access.set(get_edit_access.result())

    @render.ui
    def profile():
        info = user_info.get()
        contents = []
        if "name" in info:
            contents.append(ui.card_header(ui.markdown(f"Hello **{info['name']}**")))
        if "resource_access" in info:
            try:
                contents.append(
                    ui.p(
                        f"Roles: {', '.join(info['resource_access']['concierge-auth']['roles'])}"
                    )
                )
            except KeyError:
                pass
        if "email" in info:
            contents.append(ui.p(f"Email: {info['email']}"))
        return ui.card(*contents)

    @render.ui
    def home_text():
        auth_is_enabled = auth_enabled()
        items = [title]
        if not auth_is_enabled or edit_access.get():
            items.append(quickstart)
        elif read_access.get():
            items.append(quickstart_readonly)
        else:
            items.append(quickstart_no_access)
        items.append(tips)
        if auth_is_enabled:
            info = user_info.get()
            if info:
                try:
                    has_admin = (
                        "admin" in info["resource_access"]["concierge-auth"]["roles"]
                    )
                    if has_admin:
                        items.append(admin_tips)
                except KeyError:
                    pass
        items.append(contributing)
        elements = []
        if auth_is_enabled:
            elements.append(ui.output_ui("profile"))
        elements.append(ui.markdown("\n".join(items), render_func=md.render))
        return elements

    @reactive.effect
    def startup():
        get_read_access()
        get_edit_access(permissions.get())
