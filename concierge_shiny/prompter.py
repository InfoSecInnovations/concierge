from shiny import ui, Inputs, Outputs, Session, module, reactive, render, req
from configobj import ConfigObj
from pathlib import Path
import os
from concierge_backend_lib.prompting import load_model, get_response
from concierge_backend_lib.opensearch import get_context
from tqdm import tqdm
from util.async_generator import asyncify_generator
from components import collection_selector_ui, collection_selector_server 
from markdown_it import MarkdownIt
from mdit_py_plugins import attrs

md = MarkdownIt("gfm-like").use(attrs.attrs_plugin)

REFERENCE_LIMIT = 5

def load_config(dir):
    files = os.listdir(Path('prompter_config', dir).as_posix())
    return { file.replace('.concierge', ''): ConfigObj(
        Path('prompter_config', dir, file).as_posix(), list_values=False
    ) for file in filter(lambda file: file.endswith('.concierge'), files)}

tasks = load_config('tasks')
personas = load_config('personas')
enhancers = load_config('enhancers') 

# --------
# MESSAGE ITEM
# --------

@module.ui
def message_ui():
    return ui.output_ui("message_content")

@module.server
def message_server(input: Inputs, output: Outputs, session: Session, message):
    @render.ui
    def message_content():
        return ui.card(
            ui.markdown(message["content"], render_func=md.render),
            class_="text-primary" if message["role"] == "assistant" else None
        )

@module.ui
def prompter_ui():
    return [
        ui.markdown("# Prompter"),
        ui.output_ui("prompter_ui")      
    ]

# --------
# MAIN
# --------

@module.server
def prompter_server(input: Inputs, output: Outputs, session: Session, upload_dir, selected_collection, collections, opensearch_status, client, ollama_status):

    llm_loaded = reactive.value(False)
    messages = reactive.value([])
    current_message = reactive.value({})
    processing = reactive.value(False)
    # We're going to indepedently set the "prompt" when either
    # * the submit button is pressed
    # * the Enter button is pressed
    prompt = reactive.value(None)
    current_file_id = reactive.value(0)

    id_enter = module.resolve_id("enter")

    collection_selector_server("collection_selector", selected_collection, collections)

    @reactive.extended_task
    async def load_llm_model():
        print("Checking language model...")
        pbar = None
        with ui.Progress() as p:
            p.set(value=0, message="Loading Language Model...")
            async for progress in asyncify_generator(load_model()):
                if not pbar:
                    pbar = tqdm(
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        desc="Loading Language Model"
                        )
                pbar.total = progress[1]
                p.max = progress[1]
                # slight hackiness to set the initial value if resuming a download or switching files
                if pbar.initial == 0 or pbar.initial > progress[0]:
                    pbar.initial = progress[0]
                p.set(value=progress[0], message=f"Loading Language Model: {progress[0]}/{progress[1]}")
                pbar.n = progress[0]
                pbar.refresh()
        if pbar:
            pbar.close()   
        llm_loaded.set(True) 
        print("Language model loaded.\n")
        ui.notification_show("Language model loaded")  

    @reactive.effect
    def init():
        if ollama_status.get() and not llm_loaded.get():
            load_llm_model()

    @render.ui
    def prompter_ui():
        loaded = llm_loaded.get() and ollama_status.get() and opensearch_status.get()
        if loaded:
            task_list = list(tasks)
            selected_task = task_list[0] if 'question' not in tasks else 'question'
            if "task_select" in input and input.task_select() in tasks:
                selected_task = input.task_select()
            return ui.TagList(
                ui.output_ui("message_list"),
                ui.output_ui("current_message_view"),
                ui.markdown("Please create a collection and ingest some documents into it first!") if not len(collections.get()) else
                ui.div(
                    ui.row(
                        ui.column(9, ui.input_text(id="chat_input", label=None, placeholder=tasks[selected_task]["greeting"], width="100%")),
                        ui.column(3, ui.input_task_button(id="chat_submit", label="Chat"))
                    ),                   
                    {
                        "class": "chat-text-input",
                        # We'll use this ID in the JavaScript to report the prompt value
                        # so the Shiny app can call `input.enter()` inside the module
                        "data-enter-id": id_enter
                    }
                ),
                collection_selector_ui("collection_selector"),
                ui.layout_columns(
                    ui.input_select(id="task_select", label="Task", choices=task_list, selected=selected_task),
                    ui.input_select(id="persona_select", label="Persona", choices=['None', *personas.keys()]),
                    ui.input_select(id="enhancers_select", label="Enhancers", choices=list(enhancers), multiple=True)
                ),
                ui.output_ui("file_input"),
                ui.include_js(os.path.abspath(os.path.join(os.path.dirname(__file__), 'js', 'chat_input.js')), method='inline'),              
            )
        else:
            if not ollama_status.get() or not opensearch_status.get():
                return ui.markdown("Requirements are not online, see sidebar!")
            return ui.markdown("Loading Language Model, please wait...")

    @render.ui
    def current_message_view():
        message_value = current_message.get()
        if not len(message_value):
            return None
        message_server("current_message", message_value)
        return message_ui("current_message")

    def stream_response(collection_name, user_input, task, persona, selected_enhancers, source_file):
        context = get_context(client, collection_name, REFERENCE_LIMIT, user_input)
        if len(context["sources"]):
            yield 'Responding based on the following sources:\n\n'
            for source in context["sources"]:
                metadata = source["metadata"]
                if source["type"] == "pdf":
                    yield f'   PDF File: [page {metadata["page"]} of {metadata["filename"]}](<uploads/{metadata["filename"]}#page={metadata["page"]}>){{target="_blank"}}\n\n'
                if source["type"] == "web":
                    yield f'   Web page: <{metadata["source"]}>{{target="_blank"}} scraped {metadata["ingest_date"]}\n\n'
            if "prompt" in tasks[task]:
                yield get_response(
                    context["context"], 
                    tasks[task]["prompt"], 
                    user_input,
                    None if not persona or persona == 'None' else personas[persona]["prompt"],
                    None if not selected_enhancers else [enhancers[enhancer]["prompt"] for enhancer in selected_enhancers],
                    source_file
                )
        else:
            yield "No sources were found matching your query. Please refine your request to closer match the data in the database or ingest more data."

    @ui.bind_task_button(button_id="chat_submit")
    @reactive.extended_task
    async def process_chat(collection_name, user_input, task, persona, selected_enhancers, source_file):       
            message_text = ""
            current_message.set({})
            async for x in asyncify_generator(stream_response(collection_name, user_input, task, persona, selected_enhancers, source_file)):
                print(f"chat output: {x}")
                message_text += x
                async with reactive.lock():
                    current_message.set({"role": "assistant", "content": message_text})
                    await reactive.flush()
            processing.set(False)

    # on click chat submit
    @reactive.effect
    @reactive.event(input.chat_submit)
    def chat_prompt():
        prompt.set(input.chat_input())

    # on press enter in chat box
    @reactive.effect
    @reactive.event(input.enter)
    def chat_prompt():
        # only submit message if processing is done
        if processing.get():
            return
        # input.enter() reports the value of the text input field
        # because it's easy for users to press Enter quickly while typing
        # before input.chat_input() has had a chance to update
        prompt.set(input.enter())

    @reactive.effect
    @reactive.event(prompt, ignore_init=True, ignore_none=True)
    def send_chat():
        user_input = prompt.get()
        # for some reason ignore_none isn't always catching this, maybe because the value is ""?
        if not user_input:
            return
        processing.set(True)
        ui.update_text("chat_input", value="")
        collection_name = selected_collection.get()
        task = input.task_select()
        persona = input.persona_select()
        if persona == "None":
            persona = None
        selected_enhancers = input.enhancers_select()
        full_message = f'Task: {task}'
        if persona and persona != 'None':
            full_message += f', Persona: {persona}'
        if selected_enhancers and len(selected_enhancers):
            full_message += f', Enhancers: {selected_enhancers}'
        full_message += f'.\n\nCollection: {collection_name}'


        input_files = input[f"prompt_file_{current_file_id.get()}"]()
        file_contents = None
        if input_files and len(input_files):
            with open(input_files[0]["datapath"], "r") as file:
                file_contents = file.read()
            full_message += f'\n\nFile: {input_files[0]["name"]}'
        full_message += f'\n\nInput: {user_input}'
        messages.set(messages.get() + [{"role": "user", "content": full_message}])
        process_chat(collection_name, user_input, task, persona, selected_enhancers, file_contents)

    @reactive.effect
    @reactive.event(processing, ignore_none=False, ignore_init=True)
    def add_message():
        # only add message if processing is done
        if processing.get():
            return
        messages.set(messages.get() + [current_message.get()])
        current_message.set({})
        # we do this to allow the user to sumbit the same prompt twice
        prompt.set(None)
        # this will clear the file input
        current_file_id.set(current_file_id.get() + 1)

    @render.ui
    @reactive.event(current_file_id, ignore_none=False, ignore_init=False)
    def file_input():
        return ui.input_file(id=f"prompt_file_{current_file_id.get()}", label="Source File (optional)")

    @render.ui
    def message_list():
        return [message_ui(f"message_{i}") for i, message in enumerate(messages.get())]
    
    @reactive.effect
    def message_servers():
        for i, message in enumerate(messages.get()):
            message_server(f"message_{i}", message)
