from shiny import ui, Inputs, Outputs, Session, App
from markdown_it import MarkdownIt
from mdit_py_plugins import attrs

md = MarkdownIt("gfm-like").use(attrs.attrs_plugin)

app_ui = ui.page_auto(
    ui.chat_ui("prompter_chat"),
    ui.markdown('[Google](<https://www.google.com>){target="_blank"}', render_func=md.render)
)

def server(input: Inputs, output: Outputs, session: Session):
    chat = ui.Chat(id="prompter_chat")

    # this is supposed to make the markdown render properly
    # it outputs the correct HTML, but the actual HTML in the browser is missing target="_blank"
    @chat.transform_assistant_response
    def render_md(s: str):
        print(md.render(s))
        return ui.HTML(md.render(f"Rendered:\n\n{s}"))
    
    @chat.on_user_submit
    async def on_chat_submit(user_input: str):
        await chat.append_message('[Google](<https://www.google.com>){target="_blank"}')
        

app = App(app_ui, server)