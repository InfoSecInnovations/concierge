from shiny import ui, Inputs, Outputs, Session, module, reactive, render
from ..common.collection_selector_ui import collection_selector_ui
from .collection_selector_server import collection_selector_server
from ..common.markdown_renderer import md
from concierge_api_client import ConciergeClient
from .collections_data import CollectionsData
import asyncio
import humanize
import tqdm
from concierge_types import TaskInfo, PromptConfigInfo

REFERENCE_LIMIT = 5


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
    client: ConciergeClient,
    selected_collection: reactive.Value,
    collections: reactive.Value[CollectionsData],
    opensearch_status: reactive.Value,
    ollama_status: reactive.Value
):
    llm_loaded = reactive.value(False)
    current_file_id = reactive.value(0)
    tasks: reactive.Value[dict[str, TaskInfo] | None] = reactive.value(None)
    personas: reactive.Value[dict[str, PromptConfigInfo] | None] = reactive.value(None)
    enhancers: reactive.Value[dict[str, PromptConfigInfo] | None]  = reactive.value(None)

    @reactive.extended_task
    async def load_prompter_config():
        return await asyncio.gather(client.get_tasks(), client.get_personas(), client.get_enhancers())
    
    @reactive.effect
    def load_config_effect():
        tasks_result, personas_result, enhancers_result = load_prompter_config.result()
        tasks.set(tasks_result)
        personas.set(personas_result)
        enhancers.set(enhancers_result)

    collection_selector_server(
        "collection_selector", selected_collection, collections
    )
    chat = ui.Chat(id="prompter_chat")

    @chat.transform_assistant_response
    def render_md(s: str):
        return md.render(s)

    @reactive.extended_task
    async def load_prompting_llm_model(model_name: str):
        print(f"Checking {model_name} language model...")
        pbar = None
        with ui.Progress() as p:
            p.set(value=0, message=f"Loading {model_name} Language Model...")
            async for progress in client.load_model(model_name):
                if not pbar:
                    pbar = tqdm(
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"Loading {model_name} Language Model",
                    )
                pbar.total = progress[1]
                p.max = progress[1]
                # slight hackiness to set the initial value if resuming a download or switching files
                if pbar.initial == 0 or pbar.initial > progress[0]:
                    pbar.initial = progress[0]
                p.set(
                    value=progress[0],
                    message=f"Loading {model_name} Language Model: {humanize.naturalsize(progress[0], binary=True)}/{humanize.naturalsize(progress[1], binary=True)}",
                )
                pbar.n = progress[0]
                pbar.refresh()
        if pbar:
            pbar.close()
        print(f"{model_name} language model loaded.\n")
        ui.notification_show(f"{model_name} Language Model loaded")

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
        loaded = llm_loaded.get() and ollama_status.get() and opensearch_status.get() and tasks.get()
        if loaded:
            if not len(collections.get().collections):
                return ui.markdown(
                    "Please create a collection and ingest some documents into it first!"
                )
            return ui.output_ui("chat_area")
        if not ollama_status.get() or not opensearch_status.get():
            return ui.markdown("Requirements are not online, see sidebar!")
        if not tasks.get():
            return ui.markdown("Loading prompter config, please wait...")
        return ui.markdown("Loading Language Model, please wait...")

    @render.ui
    def chat_area():
        tasks_dict = tasks.get()
        task_list = list(tasks_dict)
        selected_task = task_list[0] if "question" not in tasks_dict else "question"
        return ui.TagList(
            ui.chat_ui(
                id="prompter_chat",
                placeholder=tasks_dict[selected_task].greeting,
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
                    choices=["None", *personas.get().keys()],
                ),
                ui.input_select(
                    id="enhancers_select",
                    label="Enhancers",
                    choices=list(enhancers.get()),
                    multiple=True,
                ),
            ),
            ui.output_ui("file_input"),
        )

    @reactive.effect
    @reactive.event(input.task_select)
    def update_chat_placeholder():
        tasks_dict = tasks.get()
        selected_task = input.task_select()
        task_list = list(tasks_dict)
        if selected_task in task_list:
            chat.update_user_input(placeholder=tasks_dict[selected_task].greeting)

    async def stream_response(
        collection_id: str, user_input: str, task: str, persona: str | None, selected_enhancers: list[str] | None, source_file: str | None
    ):
        # async def do_get_context(token):
        #     return await get_context(
        #         token["access_token"], collection_id, REFERENCE_LIMIT, user_input
        #     )

        # context = await task_runner.run_async_task(do_get_context)
        # if len(context["sources"]):
        #     yield "Responding based on the following sources:\n\n"
        #     for source in context["sources"]:
        #         yield f"{page_link(collection_id, source)}\n\n"
        #     if "prompt" in tasks[task]:
        #         yield await get_response(
        #             context["context"],
        #             tasks[task]["prompt"],
        #             user_input,
        #             None
        #             if not persona or persona == "None"
        #             else personas[persona]["prompt"],
        #             None
        #             if not selected_enhancers
        #             else [
        #                 enhancers[enhancer]["prompt"] for enhancer in selected_enhancers
        #             ],
        #             source_file,
        #         )
        # else:
        #     yield "No sources were found matching your query. Please refine your request to closer match the data in the database or ingest more data."
        # TODO: file
        async for x in client.prompt(collection_id, user_input, task, None if not persona or persona == "None" else persona, selected_enhancers):
            # TODO: yield sources
            yield x

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
    
    @reactive.effect
    def update_config():
        load_prompter_config()
