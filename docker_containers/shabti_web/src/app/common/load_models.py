from shabti_api_client import BaseShabtiClient
from shiny.session import require_active_session
from .toasts import ProgressRow, ProgressToast, show_message
from tqdm import tqdm

_model_toasts: dict[str, ProgressToast] = {}


def model_load_toast() -> ProgressToast:
    """The one toast every model load in this session shares.

    Keyed on the root session rather than passed in, because the embeddings model and the chat model
    are loaded from two different module servers - and two toasts for what is one activity is what
    this replaces. `root_scope` returns the same object from either of them.
    """
    root = require_active_session(None).root_scope()
    if root.id not in _model_toasts:
        _model_toasts[root.id] = ProgressToast(
            "model-loading", "Loading models", hide_when_empty=True
        )
        root.on_ended(lambda: _model_toasts.pop(root.id, None))
    return _model_toasts[root.id]


async def load_models(client: BaseShabtiClient, *model_names: str):
    toast = model_load_toast()
    for model_name in model_names:
        print(f"Checking {model_name} language model...")
        pbar = None
        last_percent = None
        try:
            async for load_info in client.load_model(model_name):
                if not pbar:
                    # the row goes up on the first thing the stream actually says: a model that is
                    # already loaded or sleeping yields nothing at all, and would otherwise leave
                    # an empty row on screen for as long as the check took
                    pbar = tqdm(total=1, desc=f"Loading {model_name} Language Model")
                # `total` is always 1 and `progress` is already a fraction of it, so this is a
                # percentage rather than a ratio of two counts
                percent = round(load_info.progress * 100)
                pbar.n = load_info.progress
                pbar.refresh()
                if percent == last_percent:
                    # the host can report the same percent many times over; there is nothing to
                    # redraw for those
                    continue
                last_percent = percent
                await toast.set_row(
                    ProgressRow(
                        key=model_name,
                        label=model_name,
                        # the stream's own word for what it is doing, which nothing used to show
                        detail=load_info.info or "",
                        percent=percent,
                    )
                )
        finally:
            # including on the way out of a failed load, or the row would sit there for ever saying
            # the model is still loading. the last one out takes the toast down with it
            await toast.drop_row(model_name)
            if pbar:
                pbar.close()
        print(f"{model_name} language model loaded.\n")
        show_message(f"{model_name} Language Model loaded")
