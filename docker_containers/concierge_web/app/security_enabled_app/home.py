from shiny import ui, Inputs, Outputs, Session, render, module, reactive
from ..common.markdown_renderer import md
from ..common.home_texts import TITLE, QUICKSTART, TIPS, CONTRIBUTING


@module.ui
def home_ui():
    return ui.output_ui("home_text")


@module.server
def home_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    user_info
):
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
        return [
            ui.output_ui("profile"),
            ui.markdown("\n".join([TITLE, QUICKSTART, TIPS, CONTRIBUTING]), render_func=md.render)
        ]
