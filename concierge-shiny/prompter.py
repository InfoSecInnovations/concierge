from shiny import ui, Inputs, Outputs, Session, module, reactive, render
from configobj import ConfigObj
from pathlib import Path
import os
from concierge_backend_lib.prompting import load_model, get_context, get_response
from tqdm import tqdm
import time
import asyncio
import concurrent.futures

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

    def load_llm_model():
        print("Checking language model...")
        dummyp = tqdm(desc="Dummy loading", total=4)
        for i in range(4):
            time.sleep(1)
            dummyp.n = i+1
            dummyp.refresh()
        dummyp.close()
        pbar = None
        for progress in load_model():
            if not pbar:
                pbar = tqdm(
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc="Loading Language Model"
                )
            # slight hackiness to set the initial value if resuming a download or switching files
            if pbar.initial == 0 or pbar.initial > progress[0]:
                pbar.initial = progress[0]
            pbar.total = progress[1]
            pbar.n = progress[0]
            pbar.refresh()
        if pbar:
            pbar.close()      
        print("Language model loaded.\n")   

    @reactive.extended_task
    async def init_llm():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(pool, load_llm_model)
        llm_loaded.set(True)

    @reactive.effect
    def init():
        init_llm()

    @render.ui
    def prompter_ui():
        loaded = llm_loaded.get()
        if loaded:
            return ui.markdown("TODO: prompter UI")
        else:
            return ui.markdown("Loading Language Model...")
