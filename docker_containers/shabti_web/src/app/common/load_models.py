from shiny import ui
from shabti_api_client import BaseShabtiClient
from tqdm import tqdm


async def load_models(client: BaseShabtiClient, *model_names: str):
    for model_name in model_names:
        print(f"Checking {model_name} language model...")
        pbar = None
        with ui.Progress() as p:
            p.set(value=0, message=f"Loading {model_name} Language Model...")
            async for load_info in client.load_model(model_name):
                if not pbar:
                    pbar = tqdm(
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"Loading {model_name} Language Model",
                    )
                pbar.total = load_info.total
                p.max = load_info.total
                # slight hackiness to set the initial value if resuming a download or switching files
                if pbar.initial == 0 or pbar.initial > load_info.progress:
                    pbar.initial = load_info.progress
                p.set(
                    value=load_info.progress,
                    message=f"Loading {model_name} Language Model...",
                )
                pbar.n = load_info.progress
                pbar.refresh()
        if pbar:
            pbar.close()
        print(f"{model_name} language model loaded.\n")
        ui.notification_show(f"{model_name} Language Model loaded")
