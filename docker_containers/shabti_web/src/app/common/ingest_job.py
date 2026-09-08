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


def item_label(item: IngestItemInfo) -> str:
    """What to call an item on screen.

    An item the request never knew about is seeded from whatever event discovered it, and a failure's
    label can be empty, so the error's filename gets a look in before the id does.
    """
    if item.label:
        return item.label
    if item.error and item.error.filename:
        return item.error.filename
    return item.item_id


def item_row(item: IngestItemInfo) -> ProgressRow:
    """One bar for an item that has reported progress."""
    parts = max(item.info.total, 1)
    # progress is the zero indexed part, which is what the "+ 1" is for. clamped because a crawl's
    # total is an upper bound it revises down - "produced so far, plus one if still going" - so the
    # numerator can otherwise overtake it
    part = min(item.info.progress + 1, parts)
    return ProgressRow(
        key=item.item_id,
        label=item_label(item),
        detail=f"part {part} of {parts}",
        percent=round(part / parts * 100),
    )


def flash_row(item: IngestItemInfo) -> ProgressRow:
    """A finished item's one poll of colour, before it leaves the toast.

    Full whatever the counts said, because this reports an outcome rather than a position - and a
    crawl's `total` is an upper bound it revises down, so a finished document can sit at "part 3 of
    5". `info` is no guide to which outcome either: an expanded archive never had one, a file that
    failed in its loader has none, and one that failed on its last page has a nearly complete one.
    So the two fields that only ever mean one thing are read first.
    """
    if item.error is not None:
        return ProgressRow(
            key=item.item_id,
            label=item_label(item),
            # `error` is the type name and `message` the sentence, so prefer the sentence
            detail=item.error.message or item.error.error,
            percent=100,
            variant="danger",
        )
    if item.expanded is not None:
        # an archive that produced nothing was still handled, and this is the only line that says
        # so: it has no document of its own to report complete
        return ProgressRow(
            key=item.item_id,
            label=item_label(item),
            detail=f"expanded into {item.expanded} files",
            percent=100,
            variant="success",
        )
    return ProgressRow(
        key=item.item_id,
        label=item_label(item),
        detail="done",
        percent=100,
        variant="success",
    )


def progress_rows(
    job: IngestInfo,
    cancelling: bool,
    collection_name: str | None,
    flashing: set[str] | None = None,
) -> tuple[list[ProgressRow], str]:
    """A bar per item being worked on, and the line of text above them.

    Only items that have actually reported progress get a bar of their own. The API has no "item
    started" event - `info` appears once an item has written its first page, and the slow part of a
    file, the parse, happens before that - so an item holding a worker slot is indistinguishable from
    a queued one. Without the `preparing` row below, a job full of unparsed files would show no bars.

    `flashing` is the items that finished since the last poll. They get a full coloured bar for this
    one poll so that work which came and went between two polls is still seen happening.
    """
    done = [item for item in job.items if item_done(item)]
    unfinished = [item for item in job.items if not item_done(item)]
    started = [item for item in unfinished if item.info is not None]
    active = [item_row(item) for item in started]
    if not active and unfinished and is_active(job):
        active = [
            ProgressRow(
                key=unfinished[0].item_id,
                label=item_label(unfinished[0]),
                detail="preparing...",
                # no number to show yet, so an indeterminate bar rather than a stalled empty one
                percent=None,
            )
        ]
    # in `job.items` order rather than `flashing` order, or the rows reshuffle every poll
    flash = [flash_row(item) for item in job.items if item.item_id in (flashing or ())]
    # the denominator moves: a zip expands into an item per member, which join the same job
    count = f"{len(done)} of {len(job.items)} {item_kind(job)}"
    # against the active rows, so neither the flashes nor the overall bar are counted as waiting
    queued = len(unfinished) - len(active)
    if queued > 0 and is_active(job):
        count = f"{count}, {queued} queued"
    overall = (
        [
            ProgressRow(
                key="total",
                label="Overall",
                # the count belongs under the bar it describes, which is what a row's detail is
                detail=count,
                # completed items only, so the bar never disagrees with the count beneath it
                percent=round(len(done) / len(job.items) * 100),
            )
        ]
        # nothing to summarise when the job is one item and the row below already says it all
        if len(job.items) > 1
        else []
    )
    rows = [*overall, *active, *flash]
    if cancelling and is_active(job):
        # only while it is still unwinding: the last update of a cancelled job lands after it has
        # stopped, and "cancelling..." on a job that is over reads as stuck
        status = "cancelling..."
    else:
        # with an overall bar the count is already under it, and this line is left to say only what
        # qualifies the job as a whole. without one there is no bar for it to sit under
        status = "" if overall else count
    if collection_name:
        status = f"{status} - {collection_name}" if status else collection_name
    return rows, status


def done_message(job: IngestInfo, collection_name: str | None) -> tuple[str, str]:
    """What the toast that replaces the progress one says, and what colour it is."""
    where = f" into {collection_name}" if collection_name else ""
    if job.status == IngestStatus.COMPLETE:
        failed = len([item for item in job.items if item.error is not None])
        if failed:
            # a job only fails when its worker raises, so a batch where most of the files were
            # unreadable still ends "complete". saying so here is the one report of a per item
            # failure that a reload or a late poll can't lose
            return (
                f"Ingested {len(job.items) - failed} of {len(job.items)} "
                f"{item_kind(job)}{where}, {failed} failed",
                "warning",
            )
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
