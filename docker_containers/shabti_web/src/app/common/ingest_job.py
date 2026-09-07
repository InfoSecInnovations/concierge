"""One ingest job as it appears in its toast.

An ingest outlives the session that started it, so a toast is a view of `GET /ingests` rather than
of anything this session remembers.

The toast is shown exactly once. Its bars are built and patched by the shared progress handler, so
nothing Shiny rendered is ever re-rendered - which is what keeps the Cancel button bound. Re-showing
a toast on an id that is already up would remove the element and insert a new one, rebinding that
button at zero and reporting the zero back as a click.
"""

from shiny import module, reactive, ui, Inputs, Outputs, Session
from shabti_api_client import BaseShabtiClient
from shabti_types import IngestInfo, IngestItemInfo, IngestStatus, IngestNotFoundError
from .collections_data import CollectionsData
from .toasts import ProgressRow, ProgressToast, show_message

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


def collection_label(
    job: IngestInfo,
    collections: reactive.Value[CollectionsData],
    selected_collection: reactive.Value,
) -> str | None:
    """The job's collection name, when it isn't the one on screen.

    Jobs span collections, so a toast has to say which one it belongs to unless that is obvious.
    """
    known = collections.get().collections
    if job.collection_id == selected_collection.get() or job.collection_id not in known:
        return None
    return known[job.collection_id].collection_name


def item_done(item: IngestItemInfo) -> bool:
    """Nothing more is going to happen to this item.

    An archive has no document of its own - its members each became an item - so `expanded` is the
    only thing that ever marks one finished, and without it an archive reads as queued for ever.
    """
    return (
        item.error is not None
        or item.expanded is not None
        or (item.info is not None and item.info.complete)
    )


def item_row(item: IngestItemInfo) -> ProgressRow:
    """One bar for an item that has reported progress."""
    parts = max(item.info.total, 1)
    # progress is the zero indexed part, which is what the "+ 1" is for. clamped because a crawl's
    # total is an upper bound it revises down - "produced so far, plus one if still going" - so the
    # numerator can otherwise overtake it
    part = min(item.info.progress + 1, parts)
    return ProgressRow(
        key=item.item_id,
        label=item.label or item.item_id,
        detail=f"part {part} of {parts}",
        percent=round(part / parts * 100),
    )


def progress_rows(
    job: IngestInfo, cancelling: bool, collection_name: str | None
) -> tuple[list[ProgressRow], str]:
    """A bar per item being worked on, and the line of text above them.

    Only items that have actually reported progress get a bar. The API has no "item started" event -
    `info` appears once an item has written its first page, and the slow part of a file, the parse,
    happens before that - so an item holding a worker slot is indistinguishable from a queued one.
    Without the `preparing` row below, a job full of unparsed files would show no bars at all.
    """
    done = [item for item in job.items if item_done(item)]
    unfinished = [item for item in job.items if not item_done(item)]
    started = [item for item in unfinished if item.info is not None]
    rows = [item_row(item) for item in started]
    if not rows and unfinished and is_active(job):
        rows = [
            ProgressRow(
                key=unfinished[0].item_id,
                label=unfinished[0].label or unfinished[0].item_id,
                detail="preparing...",
                # no number to show yet, so an indeterminate bar rather than a stalled empty one
                percent=None,
            )
        ]
    if cancelling:
        return rows, "cancelling..."
    # the denominator moves: a zip expands into an item per member, which join the same job
    status = f"{len(done)} of {len(job.items)} {item_kind(job)}"
    # against the rows rather than `started`, so the item shown as preparing isn't also counted
    # as waiting to start
    queued = len(unfinished) - len(rows)
    if queued > 0:
        status = f"{status}, {queued} queued"
    if collection_name:
        status = f"{status} - {collection_name}"
    return rows, status


def done_message(job: IngestInfo, collection_name: str | None) -> tuple[str, str]:
    """What the toast that replaces the progress one says, and what colour it is."""
    where = f" into {collection_name}" if collection_name else ""
    if job.status == IngestStatus.COMPLETE:
        return f"Finished ingesting {len(job.items)} {item_kind(job)}{where}", "success"
    if job.status == IngestStatus.CANCELLED:
        return f"Ingest cancelled{where}", "warning"
    return f"Ingest failed{where}: {job.error or 'unknown error'}", "danger"


@module.ui
def ingest_toast_ui():
    """The Cancel button, which sits below the shared progress body inside the same toast."""
    return ui.div(
        ui.input_action_button("cancel", "Cancel", class_="btn-sm"),
        class_="mt-2 text-end",
    )


@module.server
def ingest_toast_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    client: BaseShabtiClient,
    ingest_id: str,
    toast: ProgressToast,
    cancelling: set[str],
):
    @reactive.extended_task
    async def cancel():
        await client.cancel_ingest(ingest_id)

    @reactive.effect
    @reactive.event(input.cancel, ignore_init=True)
    async def on_cancel():
        # the DELETE waits for the ingest to unwind, up to the API's stop grace, so the listing
        # won't say "cancelled" for a while and the toast says so itself in the meantime. a plain
        # set, because the only reader is the parent's poll, which runs again a second from now
        cancelling.add(ingest_id)
        # updated in place: rendering the button again is what would fire this handler a second time
        ui.update_action_button("cancel", label="Cancelling...", disabled=True)
        # said now rather than on the next poll, which is a second away
        await toast.set_status("cancelling...")
        cancel()

    @reactive.effect
    def cancel_effect():
        # the status rather than `result()` on its own: `result()` raises its way out of the effect
        # while the DELETE is in flight, and the general `except` below would catch that instead of
        # a real failure
        if cancel.status() != "error":
            return
        try:
            cancel.result()
        except IngestNotFoundError:
            # it finished and was pruned before the DELETE landed. its toast goes when the next
            # listing doesn't have it either
            pass
        except Exception as e:
            # a denial, or the API restarting mid call. the ingest is still running and this toast
            # is the only place it can be stopped now, so give the button back
            show_message(f"Could not cancel ingest: {e}", type="danger")
            cancelling.discard(ingest_id)
            ui.update_action_button("cancel", label="Cancel", disabled=False)
