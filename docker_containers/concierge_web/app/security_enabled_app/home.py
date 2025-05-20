from shiny import ui, Inputs, Outputs, Session, render, module, req
from ..common.markdown_renderer import md
from ..common.home_texts import TITLE, QUICKSTART, TIPS, CONTRIBUTING

API_OFFLINE = """
### Getting started:

Shabti API is offline, unable to load data.
"""

LOADING = """
### Getting started:

Loading your permissions...
"""

QUICKSTART_READONLY = """
### Getting started:

Just open the Prompter page, select a collection and ask away!

If there are no collections present you will need to ask someone with write access to create one, or obtain the permission to do so yourself.
"""

QUICKSTART_NO_ACCESS = """
### Getting started:

You currently don't have permission to do anything in Concierge, please contact an administrator to be assigned the correct roles!
"""

ADMIN_TIPS = """
### Admin tips
- You can configure Keycloak to support many different login methods including OAuth and LDAP.
- Use the Keycloak administration UI to assign roles to users. Open up the Shabti realm and assign roles from the concierge-auth client.
- Once a collection has been created you can assign custom permissions to access it if you need something more granular than the provided roles.
"""


@module.ui
def home_ui():
    return ui.output_ui("home_text")


@module.server
def home_server(
    input: Inputs, output: Outputs, session: Session, user_info, permissions, api_status
):
    @render.ui
    def profile():
        info = user_info.get()
        req(info)
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
        perms = permissions.get()
        items = [TITLE]
        if not api_status.get():
            items.append(API_OFFLINE)
        elif perms is None:
            items.append(LOADING)
        elif (
            "collection:private:create" in perms
            or "collection:shared:create" in perms
            or "update" in perms
            or "delete" in perms
        ):
            items.append(QUICKSTART)
        elif "read" in perms:
            items.append(QUICKSTART_READONLY)
        else:
            items.append(QUICKSTART_NO_ACCESS)
        items.append(TIPS)
        info = user_info.get()
        if info:
            try:
                has_admin = (
                    "admin" in info["resource_access"]["concierge-auth"]["roles"]
                )
                if has_admin:
                    items.append(ADMIN_TIPS)
            except KeyError:
                pass
        items.append(CONTRIBUTING)
        return [
            ui.output_ui("profile"),
            ui.markdown("\n".join(items), render_func=md.render),
        ]
