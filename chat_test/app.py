from shiny import App, ui, module

# Create a welcome message
welcome = ui.markdown(
    """
    Hi! This is a simple Shiny `Chat` UI. Enter a message below and I will
    simply repeat it back to you. For more examples, see this
    [folder of examples](https://github.com/posit-dev/py-shiny/tree/main/examples/chat).
    """
)


@module.ui
def chat_module_ui():
    return ui.chat_ui("chat")


@module.server
def chat_module_server(input, output, session):
    chat = ui.Chat(id="chat", messages=[welcome])

    # Define a callback to run when the user submits a message
    @chat.on_user_submit
    async def submit_chat():
        # Get the user's input
        user = chat.user_input()
        # Append a response to the chat
        await chat.append_message(f"You said: {user}")


app_ui = ui.page_fillable(
    ui.panel_title("Hello Shiny Chat"),
    chat_module_ui("chat_container"),
    fillable_mobile=True,
)


def server(input, output, session):
    chat_module_server("chat_container")


app = App(app_ui, server)
