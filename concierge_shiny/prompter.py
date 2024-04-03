from shiny import ui, Inputs, Outputs, Session, module, reactive, render, req
from configobj import ConfigObj
from pathlib import Path
import os
from concierge_backend_lib.prompting import load_model, get_context, get_response
from concierge_backend_lib.collections import get_existing_collection
from tqdm import tqdm
from util.async_generator import asyncify
from components import collection_selector_ui, collection_selector_server 

REFERENCE_LIMIT = 5

def load_config(dir):
    files = os.listdir(Path('prompter_config', dir).as_posix())
    return { file.replace('.concierge', ''): ConfigObj(
        Path('prompter_config', dir, file).as_posix(), list_values=False
    ) for file in filter(lambda file: file.endswith('.concierge'), files)}

tasks = load_config('tasks')
personas = load_config('personas')
enhancers = load_config('enhancers') 

@module.ui
def message_ui():
    return ui.output_ui("message_content")

@module.server
def message_server(input: Inputs, output: Outputs, session: Session, message):
    @render.ui
    def message_content():
        return ui.card(
            ui.markdown(message["content"])
        )

@module.ui
def prompter_ui():
    return [
        ui.markdown("# Prompter"),
        ui.output_ui("prompter_ui")
    ]

@module.server
def prompter_server(input: Inputs, output: Outputs, session: Session, upload_dir, selected_collection, collections):

    llm_loaded = reactive.value(False)
    messages = reactive.value([])
    current_message = reactive.value({})
    message_complete_trigger = reactive.value(0)

    collection_selector_server("collection_selector", selected_collection, collections)

    @reactive.extended_task
    async def load_llm_model():
        print("Checking language model...")
        pbar = None
        with ui.Progress() as p:
            p.set(value=0, message="Loading Language Model...")
            async for progress in asyncify(load_model()):
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
        load_llm_model()

    @render.ui
    def prompter_ui():
        loaded = llm_loaded.get()
        if loaded:
            return ui.TagList(
                ui.output_ui("message_list"),
                ui.output_ui("current_message_view"),
                collection_selector_ui("collection_selector"),
                ui.layout_columns(
                    ui.input_selectize(id="task_select", label="Task", choices=list(tasks), selected=None if 'question' not in tasks else 'question'),
                    ui.input_selectize(id="persona_select", label="Persona", choices=['None', *personas.keys()]),
                    ui.input_selectize(id="enhancers_select", label="Enhancers", choices=list(enhancers), multiple=True)
                ),
                ui.input_file(id="prompt_file", label="Source File (optional)"),
                ui.markdown("Please create a collection and ingest some documents into it first!") if not len(collections.get()) else
                ui.layout_columns(
                    ui.input_text(id="chat_input", label=None, placeholder="TODO: get placeholder from current task"),
                    ui.input_task_button(id="chat_submit", label="Chat")
                )
                
            )
        else:
            return ui.markdown("Loading Language Model, please wait...")

    @render.ui
    def current_message_view():
        message_value = current_message.get()
        if not len(message_value):
            return None
        message_server("current_message", message_value)
        return message_ui("current_message")

    def stream_response(collection_name, user_input, task, persona, selected_enhancers):
        collection = get_existing_collection(collection_name)
        context = get_context(collection, REFERENCE_LIMIT, user_input)
        if len(context["sources"]):
            yield 'Responding based on the following sources:\n\n'
            for source in context["sources"]:
                metadata = source["metadata"]
                if source["type"] == "pdf":
                    yield f'   PDF File: [page {metadata["page"]} of {metadata["filename"]}](<uploads/{metadata["filename"]}#page={metadata["page"]}>)\n\n'
                if source["type"] == "web":
                    yield f'   Web page: {metadata["source"]} scraped {metadata["ingest_date"]}\n\n'              
            if "prompt" in tasks[task]:
                yield get_response(
                    context["context"], 
                    tasks[task]["prompt"], 
                    user_input,
                    None if not persona or persona == 'None' else personas[persona]["prompt"],
                    None if not selected_enhancers else [enhancers[enhancer]["prompt"] for enhancer in selected_enhancers],
                    # None if not source_file else source_file.getvalue().decode()
                )
        else:
            yield "No sources were found matching your query. Please refine your request to closer match the data in the database or ingest more data."

    @ui.bind_task_button(button_id="chat_submit")
    @reactive.extended_task
    async def process_chat(collection_name, user_input, task, persona, selected_enhancers, current_trigger):
        message_text = ""
        current_message.set({})
        async for x in asyncify(stream_response(collection_name, user_input, task, persona, selected_enhancers)):
            print(f"chat output: {x}")
            message_text += x
            current_message.set({"role": "assistant", "content": message_text})
        message_complete_trigger.set(current_trigger + 1)

    @reactive.effect
    @reactive.event(input.chat_submit, ignore_init=True)
    def send_chat():
        req(input.chat_input())
        user_input = input.chat_input()
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
        full_message += f'\n\nInput: {user_input}'
        messages.set(messages.get() + [{"role": "user", "content": full_message}])
        process_chat(collection_name, user_input, task, persona, selected_enhancers, message_complete_trigger.get())

    @reactive.effect
    @reactive.event(message_complete_trigger, ignore_init=True)
    def add_message():
        messages.set(messages.get() + [current_message.get()])
        current_message.set("")

    @render.ui
    def message_list():
        return [message_ui(f"message_{i}") for i, message in enumerate(messages.get())]
    
    @reactive.effect
    def message_servers():
        for i, message in enumerate(messages.get()):
            message_server(f"message_{i}", message)
