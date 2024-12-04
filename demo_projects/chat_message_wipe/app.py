from shiny import App, ui, Inputs, Outputs, Session, reactive, render

app_ui = ui.page_auto(
    ui.markdown("# Testing chat message history"),
    ui.output_ui("chat_area"),
    ui.input_action_button("toggle_chat", "Toggle Chat"),
)


def server(input: Inputs, output: Outputs, session: Session):
    chat = ui.Chat(id="test_chat")
    show_chat = reactive.value(True)

    @chat.on_user_submit
    async def on_chat_submit():
        await chat.append_message(chat.user_input())

    @render.ui
    def chat_area():
        if show_chat.get():
            # recent versions allow us to set the messages in the UI element, this fixes the issue!
            return ui.chat_ui("test_chat", messages=chat.messages())
        else:
            return ui.markdown("Chat hidden")

    @reactive.effect
    @reactive.event(input.toggle_chat, ignore_none=False, ignore_init=True)
    def toggle_chat():
        show_chat.set(not show_chat.get())


app = App(app_ui, server)
