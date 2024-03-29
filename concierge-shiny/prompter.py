from shiny import ui, Inputs, Outputs, Session, module, reactive, render
from configobj import ConfigObj
from pathlib import Path
import os
from concierge_backend_lib.prompting import load_model, get_context, get_response
from tqdm import tqdm
import time
import asyncio
import concurrent.futures
from util.async_generator import asyncify

pool = concurrent.futures.ThreadPoolExecutor()

def load_config(dir):
    files = os.listdir(Path('prompter_config', dir).as_posix())
    return { file.replace('.concierge', ''): ConfigObj(
        Path('prompter_config', dir, file).as_posix(), list_values=False
    ) for file in filter(lambda file: file.endswith('.concierge'), files)}

tasks = load_config('tasks')
personas = load_config('personas')
enhancers = load_config('enhancers') 

@module.ui
def prompter_ui():
    return [
        ui.markdown("# Prompter"),
        ui.output_ui("prompter_ui")
    ]

@module.server
def prompter_server(input: Inputs, output: Outputs, session: Session, collection, upload_dir):

    llm_loaded = reactive.value(False)
    messages = reactive.value([])

    def dummy_generator():
        for i in range(4):
            time.sleep(0.5)
            yield i

    @reactive.extended_task
    async def load_llm_model():
        print("Checking language model...")
        dummyp = tqdm(desc="Dummy loading", total=4)
        with ui.Progress(min=0, max=4) as p:
            p.set(value=0, message="Loading dummy...")
            async for i in asyncify(dummy_generator()):
                dummyp.n = i+1
                dummyp.refresh()
                p.set(value=i+1, message=f"{i+1}/4 dummy loading")
        dummyp.close()
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

    @reactive.effect
    def init():
        load_llm_model()

    @render.ui
    def prompter_ui():
        loaded = llm_loaded.get()
        if loaded:
            return ui.TagList(
                ui.markdown("TODO: messages"),
                ui.markdown("TODO: collection selector"),
                ui.input_selectize(id="task_select", label="Task", choices=list(tasks), selected=None if 'question' not in tasks else 'question'),
                ui.input_selectize(id="persona_select", label="Persona", choices=['None', *personas.keys()]),
                ui.input_selectize(id="enhancers_select", label="Enhancers", choices=list(enhancers), multiple=True),
                ui.markdown("TODO: file input"),
                ui.input_text(id="chat_input", label="Chat", placeholder="TODO: get placeholder from current task")
            )
        else:
            return ui.markdown("Loading Language Model, please wait...")
