"""One ingest job as it appears in the Ingest Jobs panel.

An ingest outlives the session that started it, so the panel is a view of `GET /ingests` rather than
of anything this session remembers. Everything here is a pure function of one `IngestInfo` except
the cancel button, which needs a server of its own to own the DELETE.
"""

from shiny import module, reactive, ui, Inputs, Outputs, Session
from shabti_api_client import BaseShabtiClient
from shabti_types import IngestInfo, IngestItemInfo, IngestStatus, IngestNotFoundError

ACTIVE_STATUSES = (IngestStatus.QUEUED, IngestStatus.RUNNING)


def is_active(job: IngestInfo) -> bool:
    return job.status in ACTIVE_STATUSES


def item_kind(job: IngestInfo) -> str:
    """files or URLs, which nothing on the job says outright.

    A URL item's label is the URL that was submitted and a file's is its filename, and a filename is
    always a basename - the browser sends no path and a zip member is basenamed - so it can't hold
    the "//" that makes this a scheme rather than a file called something like http_notes.pdf.
    """
    urls = job.items and all(
        item.label.startswith(("http://", "https://")) for item in job.items
    )
    return "URLs" if urls else "files"


def progress_bar(percent: int, class_: str = ""):
    return ui.div(
        ui.div(class_=f"progress-bar {class_}", style=f"width: {percent}%"),
        class_="progress",
        style="height: 0.5rem",
    )


def item_detail(item: IngestItemInfo):
    if item.error:
        return ui.tags.span(item.error.message, class_="small text-danger")
    if item.expanded is not None:
        # an archive has no document of its own, so it has no `info` either: checked before the
        # queued branch below, which it would otherwise fall into for ever
        return ui.TagList(
            progress_bar(100, "bg-success"),
            ui.tags.span(f"expanded into {item.expanded} files", class_="small"),
        )
    if item.info is None:
        # queued items never reach the progress stream, only the listing this panel polls
        return ui.TagList(
            progress_bar(0), ui.tags.span("queued", class_="small text-muted")
        )
    if item.info.complete:
        return ui.TagList(
            progress_bar(100, "bg-success"), ui.tags.span("done", class_="small")
        )
    # progress is the zero indexed part, which is what the "+ 1" was for when this was a toast
    total = max(item.info.total, 1)
    done = item.info.progress + 1
    return ui.TagList(
        progress_bar(round(done / total * 100)),
        ui.tags.span(f"part {done} of {total}.", class_="small"),
    )


def item_row(item: IngestItemInfo):
    # a file that failed before it had a document of its own has nothing but its error to name it
    label = item.label or (item.error.filename if item.error else None) or item.item_id
    return ui.div(
        ui.div(label, class_="col-4 text-truncate", title=label),
        ui.div(item_detail(item), class_="col-8"),
        class_="row align-items-center g-2",
    )


def ingest_job_card(job: IngestInfo, collection_name: str | None, cancelling: bool):
    header = [
        ui.div(
            f"{len(job.items)} {item_kind(job)}: "
            f"{'cancelling...' if cancelling else job.status}",
            class_="col",
        )
    ]
    if is_active(job) and not cancelling:
        header.append(ui.div(cancel_button_ui(job.ingest_id), class_="col-auto"))
    elements = [ui.div(*header, class_="row align-items-center")]
    if collection_name:
        elements.append(ui.div(collection_name, class_="small text-muted"))
    if job.error:
        elements.append(ui.div(job.error, class_="small text-danger"))
    elements.extend(item_row(item) for item in job.items)
    return ui.card(*elements)


@module.ui
def cancel_button_ui():
    return ui.input_action_button("cancel", "Cancel", class_="btn-sm")


@module.server
def cancel_button_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    client: BaseShabtiClient,
    ingest_id: str,
    cancelling: reactive.Value[set[str]],
):
    @reactive.extended_task
    async def cancel():
        await client.cancel_ingest(ingest_id)

    @reactive.effect
    def cancel_effect():
        try:
            cancel.result()
        except IngestNotFoundError:
            # it finished and was pruned before the DELETE landed, which the next poll will show
            pass
        # isolated because every job's server shares this one value: reading it reactively would
        # wake all of them on any cancellation, and each would set an equal but distinct set
        with reactive.isolate():
            cancelling.set(cancelling.get() - {ingest_id})

    @reactive.effect
    @reactive.event(input.cancel, ignore_init=True)
    def on_cancel():
        # the DELETE waits for the ingest to unwind, up to the API's stop grace, so the listing
        # won't say "cancelled" for a while and the card says so itself in the meantime
        with reactive.isolate():
            cancelling.set(cancelling.get() | {ingest_id})
        cancel()
