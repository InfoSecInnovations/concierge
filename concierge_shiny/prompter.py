from shiny import ui, Inputs, Outputs, Session, module, reactive, render
from configobj import ConfigObj
from pathlib import Path
import os
from concierge_backend_lib.prompting import get_response, get_context
from components import (
    collection_selector_ui,
    collection_selector_server,
)
from functions import page_link, load_llm_model
from markdown_renderer import md
from concierge_backend_lib.authorization import auth_enabled
from auth import WebAppAsyncTokenTaskRunner

REFERENCE_LIMIT = 5


def load_prompter_config(dir):
    files = os.listdir(Path("prompter_config", dir).as_posix())
    return {
        file.replace(".concierge", ""): ConfigObj(
            Path("prompter_config", dir, file).as_posix(), list_values=False
        )
        for file in filter(lambda file: file.endswith(".concierge"), files)
    }


tasks = load_prompter_config("tasks")
personas = load_prompter_config("personas")
enhancers = load_prompter_config("enhancers")


# --------
# MAIN
# --------


@module.ui
def prompter_ui():
    return [ui.markdown("# Prompter"), ui.output_ui("prompter_ui")]


@module.server
def prompter_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    selected_collection,
    collections,
    opensearch_status,
    ollama_status,
    task_runner: WebAppAsyncTokenTaskRunner,
    user_info,
    permissions,
):
    llm_loaded = reactive.value(False)
    current_file_id = reactive.value(0)

    collection_selector_server(
        "collection_selector", selected_collection, collections, user_info
    )
    chat = ui.Chat(id="prompter_chat")

    @chat.transform_assistant_response
    def render_md(s):
        return md.render(s)

    @reactive.extended_task
    async def load_prompting_llm_model(model_name):
        await load_llm_model(model_name)

    @reactive.effect
    def load_model_effect():
        load_prompting_llm_model.result()
        llm_loaded.set(True)

    @reactive.effect
    def init():
        if ollama_status.get() and not llm_loaded.get():
            load_prompting_llm_model("mistral")

    @render.ui
    def prompter_ui():
        loaded = llm_loaded.get() and ollama_status.get() and opensearch_status.get()
        if loaded:
            if not len(collections.get().collections):

                def can_create_collection():
                    if not auth_enabled:
                        return True
                    perms = permissions.get()
                    if (
                        "collection:private:create" in perms
                        or "collection:shared:create" in perms
                    ):
                        return True
                    return False

                if can_create_collection():
                    return ui.markdown(
                        "Please create a collection and ingest some documents into it first!"
                    )
                else:
                    return ui.markdown(
                        "You do not have access to any collections, you will need someone else to grant access or allow you to create collections."
                    )
            # TODO: if selected collection isn't readable, don't display chat (theoretically a user could be able to edit but not read a collection?)
            return ui.output_ui("chat_area")
        if not ollama_status.get() or not opensearch_status.get():
            return ui.markdown("Requirements are not online, see sidebar!")
        return ui.markdown("Loading Language Model, please wait...")

    @render.ui
    def chat_area():
        task_list = list(tasks)
        selected_task = task_list[0] if "question" not in tasks else "question"
        return ui.TagList(
            ui.chat_ui(
                id="prompter_chat",
                placeholder=tasks[selected_task]["greeting"],
                messages=chat.messages(),
            ),
            collection_selector_ui("collection_selector"),
            ui.layout_columns(
                ui.input_select(
                    id="task_select",
                    label="Task",
                    choices=task_list,
                    selected=selected_task,
                ),
                ui.input_select(
                    id="persona_select",
                    label="Persona",
                    choices=["None", *personas.keys()],
                ),
                ui.input_select(
                    id="enhancers_select",
                    label="Enhancers",
                    choices=list(enhancers),
                    multiple=True,
                ),
            ),
            ui.output_ui("file_input"),
        )

    @reactive.effect
    @reactive.event(input.task_select)
    def update_chat_placeholder():
        selected_task = input.task_select()
        task_list = list(tasks)
        if selected_task in task_list:
            chat.update_user_input(placeholder=tasks[selected_task]["greeting"])

    async def stream_response(
        collection_id, user_input, task, persona, selected_enhancers, source_file
    ):
        async def do_get_context(token):
            return await get_context(
                token["access_token"], collection_id, REFERENCE_LIMIT, user_input
            )

        context = await task_runner.run_async_task(do_get_context)
        if len(context["sources"]):
            yield "Responding based on the following sources:\n\n"
            for source in context["sources"]:
                yield f"{page_link(collection_id, source)}\n\n"
            if "prompt" in tasks[task]:
                yield await get_response(
                    context["context"],
                    tasks[task]["prompt"],
                    user_input,
                    None
                    if not persona or persona == "None"
                    else personas[persona]["prompt"],
                    None
                    if not selected_enhancers
                    else [
                        enhancers[enhancer]["prompt"] for enhancer in selected_enhancers
                    ],
                    source_file,
                )
        else:
            yield "No sources were found matching your query. Please refine your request to closer match the data in the database or ingest more data."

    @chat.on_user_submit
    async def on_chat_submit():
        collection_id = selected_collection.get()
        task = input.task_select()
        persona = input.persona_select()
        selected_enhancers = input.enhancers_select()
        input_files = input[f"prompt_file_{current_file_id.get()}"]()
        file_contents = None
        if input_files and len(input_files):
            with open(input_files[0]["datapath"], "r") as file:
                file_contents = file.read()

        await chat.append_message_stream(
            stream_response(
                collection_id,
                chat.user_input(),
                task,
                persona,
                selected_enhancers,
                file_contents,
            )
        )

    # this will trigger after the chat message has been submitted
    @reactive.effect
    @reactive.event(chat.messages, ignore_none=False, ignore_init=True)
    def on_message():
        # this will clear the file input
        current_file_id.set(current_file_id.get() + 1)

    @render.ui
    @reactive.event(current_file_id, ignore_none=False, ignore_init=False)
    def file_input():
        return ui.input_file(
            id=f"prompt_file_{current_file_id.get()}", label="Source File (optional)"
        )
