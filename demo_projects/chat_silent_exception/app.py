# We've been struggling with silent exceptions (see silent_exception_test), and one remaining one was after chat submit
# You should never set a reactive inside an async function, including the chat submit
# It's possible to listen to the chat messages reactive to trigger something after message is submitted

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
        print("chat submitted")

    # if you set a reactive here the exception from the stream will be silent

    @render.ui
    def chat_trigger():
        return ui.markdown(f"chat trigger is {after_chat_trigger.get()}")

    # listening to chat.messages with a reactive allows us to trigger setting a reactive after chat has been submitted
    @reactive.effect
    @reactive.event(chat.messages, ignore_none=False, ignore_init=True)
    def on_messages():
        print("on messages")
        after_chat_trigger.set(after_chat_trigger.get() + 1)


app = App(app_ui, server)
