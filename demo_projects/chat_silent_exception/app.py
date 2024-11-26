from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from asyncio import sleep

app_ui = ui.page_auto(
    ui.markdown("# Testing silent exception"),
    ui.chat_ui("test_chat"),
    ui.output_ui("chat_trigger"),
    ui.markdown("bottom text"),
)


def server(input: Inputs, output: Outputs, session: Session):
    chat = ui.Chat(id="test_chat")
    test_value = reactive.value(42)
    after_chat_trigger = reactive.value(0)

    async def stream_response_broken(input_value, other_value):
        yield "hello\n"
        await sleep(0.1)
        yield f"so far so good: {input_value}\n"
        await sleep(0.1)
        yield f"not so good {other_value/0}"

    @chat.on_user_submit
    async def on_chat_submit():
        await chat.append_message_stream(
            stream_response_broken(chat.user_input(), test_value.get())
        )
        after_chat_trigger.set(after_chat_trigger.get() + 1)

    @render.ui
    def chat_trigger():
        return ui.markdown(f"chat trigger is {after_chat_trigger.get()}")


app = App(app_ui, server)
