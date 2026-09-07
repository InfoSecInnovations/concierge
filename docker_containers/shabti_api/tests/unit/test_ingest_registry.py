"""The registry on its own, with hand written workers in place of an ingest.

Nothing here touches OpenSearch, Tika or an embeddings server: `start` takes its worker as a
callable and the sweep's delete is injected, so the whole state machine is testable with no stack.
"""

import asyncio

import pytest
from isi_util.stream_pool import PoolValue, StreamPool
from shabti_types import (
    DocumentIngestError,
    DocumentIngestInfo,
    IngestItemInfo,
    IngestNotFoundError,
    IngestStatus,
)

from ...src.app.functionality.ingest_events import (
    ItemExpanded,
    ItemFailed,
    ItemProgress,
    ItemQueued,
)
from ...src.app.functionality.ingest_registry import (
    IngestRegistry,
    IngestTask,
    stream_ingest,
)


def info(item_id: str, progress: int = 0, complete: bool = False) -> DocumentIngestInfo:
    fields = {
        "progress": progress,
        "total": 3,
        "document_id": f"doc-{item_id}",
        "document_type": "text/plain",
        "label": item_id,
    }
    # set rather than passed as False, the way `insert` builds it
    if complete:
        fields["complete"] = True
    return DocumentIngestInfo(**fields)


def seed(*item_ids: str) -> list[IngestItemInfo]:
    return [IngestItemInfo(item_id=item_id, label=item_id) for item_id in item_ids]


def worker_of(events):
    """A worker that reports the given events and ends."""

    async def worker(_pool):
        for event in events:
            yield event

    return worker


def bare_task(*item_ids: str) -> IngestTask:
    """A task no registry ever started, for the state and fan-out behaviour on its own."""
    return IngestTask(
        "ingest", "owner", "collection", seed(*item_ids), StreamPool(1), worker_of([])
    )


class Removals:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def __call__(self, collection_id: str, document_id: str) -> None:
        self.calls.append((collection_id, document_id))


def registry(removals: Removals | None = None) -> IngestRegistry:
    return IngestRegistry(remove_document=removals or Removals())


def endless_worker(item_id: str, stopped: list[str]):
    """A worker whose job never finishes on its own, only when the pool stops it.

    Suspended in a short sleep between yields rather than in one long await, so the stop lands
    cooperatively - and its `except Exception` is what proves the throw reached the innermost frame
    where a real ingest's rollback lives.
    """

    async def worker(pool):
        async def factory():
            async def generator():
                progress = 0
                try:
                    while True:
                        progress += 1
                        yield info(item_id, progress)
                        await asyncio.sleep(0.01)
                except Exception:
                    stopped.append(item_id)
                    raise

            return generator()

        async with pool:
            pool.submit(factory, key=item_id)
            async for result in pool.results():
                if isinstance(result, PoolValue):
                    yield ItemProgress(result.key, result.value)

    return worker


def cleanup_worker(item_id: str, ran: list[str], cleaned: list[str]):
    """A worker shaped like the files one: work that must not run, cleanup that must.

    `insert_uploaded_files` deletes whatever binary no document claimed in its own `finally`, and
    that is the only thing which knows a queued ingest's uploads are sitting on disk.
    """

    async def worker(pool):
        async def factory():
            async def generator():
                ran.append(item_id)
                yield info(item_id, 1)

            return generator()

        try:
            async with pool:
                pool.submit(factory, key=item_id)
                async for result in pool.results():
                    if isinstance(result, PoolValue):
                        yield ItemProgress(result.key, result.value)
        finally:
            cleaned.append(item_id)

    return worker


async def until(predicate) -> None:
    while not predicate():
        await asyncio.sleep(0.01)


# --- the POST response and item state -------------------------------------------------------


async def test_the_post_response_carries_the_queued_items():
    reg = registry()
    snapshot = await reg.start("owner", "collection", seed("a", "b"), worker_of([]))
    assert snapshot.status == IngestStatus.RUNNING
    assert [item.item_id for item in snapshot.items] == ["a", "b"]
    # queued means no state yet, which is also what keeps them off the stream
    assert all(item.info is None and item.error is None for item in snapshot.items)
    await reg.get(snapshot.ingest_id, "owner").task


async def test_events_become_item_state():
    reg = registry()
    events = [
        ItemProgress("a", info("a", 1)),
        ItemQueued("c", "member.txt"),
        ItemFailed(
            "b", DocumentIngestError(error="EmptyDocumentError", message="", label="b")
        ),
        ItemProgress("a", info("a", 2, complete=True)),
    ]
    started = await reg.start("owner", "collection", seed("a", "b"), worker_of(events))
    task = reg.get(started.ingest_id, "owner")
    await task.task
    final = task.snapshot()
    assert final.status == IngestStatus.COMPLETE
    by_id = {item.item_id: item for item in final.items}
    # last write wins, and a member discovered mid-ingest becomes an item of its own
    assert by_id["a"].info.progress == 2 and by_id["a"].info.complete
    assert by_id["b"].error.error == "EmptyDocumentError"
    assert by_id["c"].label == "member.txt" and by_id["c"].info is None


async def test_an_expanded_archive_reports_its_member_count():
    task = bare_task("zip")
    task.apply(ItemQueued("a", "a.txt"))
    task.apply(ItemQueued("b", "b.txt"))
    task.apply(ItemExpanded("zip", 2))
    by_id = {item.item_id: item for item in task.snapshot().items}
    archive = by_id["zip"]
    # handled rather than queued for ever: it produced items instead of a document of its own
    assert archive.expanded == 2
    assert archive.info is None and archive.error is None
    assert archive.label == "zip"
    assert {by_id["a"].label, by_id["b"].label} == {"a.txt", "b.txt"}
    assert by_id["a"].expanded is None


async def test_the_snapshot_is_a_copy():
    task = bare_task("a")
    task.apply(ItemProgress("a", info("a", 1)))
    taken = task.snapshot()
    task.apply(ItemProgress("a", info("a", 2)))
    # a line serialised after the next update must not ship the newer state under it
    assert taken.items[0].info.progress == 1


# --- the stream ------------------------------------------------------------------------------


async def test_nothing_is_lost_between_subscribing_and_the_snapshot():
    task = bare_task("a")
    task.apply(ItemProgress("a", info("a", 1)))
    stream = stream_ingest(task)
    assert (await anext(stream)).progress == 1
    # applied after the snapshot was taken, so it can only arrive as an update
    task.apply(ItemProgress("a", info("a", 2)))
    assert (await anext(stream)).progress == 2
    await stream.aclose()


async def test_queued_items_are_not_streamed():
    task = bare_task("a", "b")
    task.apply(ItemProgress("a", info("a", 1)))
    task.finish(IngestStatus.COMPLETE, None)
    lines = [line async for line in stream_ingest(task)]
    assert [line.document_id for line in lines] == ["doc-a"]


async def test_an_expanded_archive_is_not_streamed():
    task = bare_task("zip")
    task.apply(ItemQueued("a", "a.txt"))
    task.apply(ItemProgress("a", info("a", 1, complete=True)))
    task.apply(ItemExpanded("zip", 1))
    task.finish(IngestStatus.COMPLETE, None)
    lines = [line async for line in stream_ingest(task)]
    # it never had a document, so there is no `document_id` a line could carry
    assert [line.document_id for line in lines] == ["doc-a"]


async def test_updates_coalesce_rather_than_queue():
    task = bare_task("a")
    stream = stream_ingest(task)
    for progress in range(5):
        task.apply(ItemProgress("a", info("a", progress)))
    # five updates while nobody was reading collapse to the latest state, not a backlog
    assert (await anext(stream)).progress == 4
    task.finish(IngestStatus.COMPLETE, None)
    assert not [line async for line in stream]


async def test_an_update_applied_as_the_ingest_ends_is_still_delivered():
    task = bare_task("a")
    stream = stream_ingest(task)
    task.apply(ItemProgress("a", info("a", 2, complete=True)))
    task.finish(IngestStatus.COMPLETE, None)
    lines = [line async for line in stream]
    assert len(lines) == 1 and lines[0].complete


async def test_an_error_is_streamed_instead_of_progress():
    task = bare_task("a")
    task.apply(ItemProgress("a", info("a", 1)))
    task.apply(
        ItemFailed(
            "a",
            DocumentIngestError(error="EmbeddingsError", message="upstream", label="a"),
        )
    )
    task.finish(IngestStatus.FAILED, "EmbeddingsError: upstream")
    lines = [line async for line in stream_ingest(task)]
    assert [line.error for line in lines] == ["EmbeddingsError"]


async def test_a_finished_ingest_streams_a_terminal_snapshot():
    reg = registry()
    started = await reg.start(
        "owner",
        "collection",
        seed("a"),
        worker_of([ItemProgress("a", info("a", 2, complete=True))]),
    )
    task = reg.get(started.ingest_id, "owner")
    await task.task
    # subscribed only after it was over: the snapshot is the whole stream, and it closes
    lines = [line async for line in stream_ingest(task)]
    assert len(lines) == 1 and lines[0].complete


# --- terminal status, cancellation and the sweep ---------------------------------------------


async def test_a_failing_worker_fails_the_ingest():
    reg = registry()

    async def worker(_pool):
        yield ItemProgress("a", info("a", 1))
        raise RuntimeError("keycloak said no")

    started = await reg.start("owner", "collection", seed("a"), worker)
    task = reg.get(started.ingest_id, "owner")
    await task.task
    final = task.snapshot()
    # nobody awaits an ingest, so this can no longer be an HTTP response
    assert final.status == IngestStatus.FAILED
    assert "keycloak said no" in final.error


async def test_cancelling_stops_the_job_and_sweeps_its_document():
    removals = Removals()
    reg = registry(removals)
    stopped: list[str] = []
    started = await reg.start(
        "owner", "collection", seed("a"), endless_worker("a", stopped)
    )
    task = reg.get(started.ingest_id, "owner")
    await until(lambda: task.snapshot().items[0].info is not None)
    final = await reg.cancel(task)
    assert final.status == IngestStatus.CANCELLED
    # the stop reached the generator itself, where a real ingest's rollback runs
    assert stopped == ["a"]
    # and the document it had started is swept, since it never reported completion
    assert removals.calls == [("collection", "doc-a")]


async def test_a_completed_document_is_not_swept():
    removals = Removals()
    reg = registry(removals)
    started = await reg.start(
        "owner",
        "collection",
        seed("a"),
        worker_of([ItemProgress("a", info("a", 2, complete=True))]),
    )
    await reg.get(started.ingest_id, "owner").task
    assert not removals.calls


async def test_an_expanded_archive_is_not_swept():
    removals = Removals()
    reg = registry(removals)
    started = await reg.start(
        "owner", "collection", seed("zip"), worker_of([ItemExpanded("zip", 2)])
    )
    await reg.get(started.ingest_id, "owner").task
    # nothing to roll back: its members own the documents, and its binary is already discarded
    assert not removals.calls


async def test_cancelling_before_the_task_has_run_is_honoured():
    reg = registry()
    stopped: list[str] = []
    started = await reg.start(
        "owner", "collection", seed("a"), endless_worker("a", stopped)
    )
    task = reg.get(started.ingest_id, "owner")
    # nothing has awaited since start, so the task has not had a turn: the pool this stops was
    # built by start rather than by the task precisely so that this works
    final = await reg.cancel(task)
    assert final.status == IngestStatus.CANCELLED


async def test_shutdown_cancels_what_is_still_running():
    reg = registry()
    stopped: list[str] = []
    started = await reg.start(
        "owner", "collection", seed("a"), endless_worker("a", stopped)
    )
    task = reg.get(started.ingest_id, "owner")
    await until(lambda: task.snapshot().items[0].info is not None)
    await reg.shutdown()
    assert task.snapshot().status == IngestStatus.CANCELLED


async def test_cancelling_a_collection_leaves_other_collections_alone():
    reg = registry()
    stopped: list[str] = []
    doomed = await reg.start("owner", "doomed", seed("a"), endless_worker("a", stopped))
    other = await reg.start("owner", "other", seed("b"), endless_worker("b", stopped))
    doomed_task = reg.get(doomed.ingest_id, "owner")
    other_task = reg.get(other.ingest_id, "owner")
    await reg.cancel_for_collection("doomed")
    assert doomed_task.snapshot().status == IngestStatus.CANCELLED
    assert other_task.snapshot().status == IngestStatus.RUNNING
    await reg.cancel(other_task)


# --- ownership, the queue and retention -------------------------------------------------------


async def test_ingests_are_scoped_to_their_owner():
    reg = registry()
    mine = await reg.start("me", "collection", seed("a"), worker_of([]))
    theirs = await reg.start("them", "collection", seed("b"), worker_of([]))
    await reg.get(mine.ingest_id, "me").task
    await reg.get(theirs.ingest_id, "them").task
    assert [item.ingest_id for item in reg.list("me")] == [mine.ingest_id]
    # a foreign id is reported exactly like a missing one, so ids aren't enumerable
    with pytest.raises(IngestNotFoundError):
        reg.get(theirs.ingest_id, "me")
    with pytest.raises(IngestNotFoundError):
        reg.get("nonexistent", "me")


async def test_an_ingest_over_the_owner_cap_is_queued_not_refused(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER", "1")
    reg = registry()
    stopped: list[str] = []
    first = await reg.start(
        "owner", "collection", seed("a"), endless_worker("a", stopped)
    )
    second = await reg.start("owner", "collection", seed("b"), worker_of([]))
    # the POST succeeded, which is the whole point: nothing is refused any more
    assert second.status == IngestStatus.QUEUED
    assert reg.get(second.ingest_id, "owner").task is None
    await reg.cancel(reg.get(first.ingest_id, "owner"))
    await reg.cancel(reg.get(second.ingest_id, "owner"))


async def test_a_freed_slot_starts_the_next_queued_ingest(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER", "1")
    reg = registry()
    stopped: list[str] = []
    first = await reg.start(
        "owner", "collection", seed("a"), endless_worker("a", stopped)
    )
    second = await reg.start(
        "owner", "collection", seed("b"), endless_worker("b", stopped)
    )
    queued = reg.get(second.ingest_id, "owner")
    await reg.cancel(reg.get(first.ingest_id, "owner"))
    await until(lambda: queued.snapshot().items[0].info is not None)
    assert queued.snapshot().status == IngestStatus.RUNNING
    await reg.cancel(queued)


async def test_a_finished_ingest_hands_its_slot_on(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER", "1")
    reg = registry()
    first = await reg.start("owner", "collection", seed("a"), worker_of([]))
    second = await reg.start("owner", "collection", seed("b"), worker_of([]))
    queued = reg.get(second.ingest_id, "owner")
    # nobody cancels anything here, so promotion has to fire from the first ingest's own ending
    await reg.get(first.ingest_id, "owner").task
    await until(lambda: queued.task is not None)
    await queued.task
    assert queued.snapshot().status == IngestStatus.COMPLETE


async def test_the_server_cap_queues_across_owners(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE", "1")
    reg = registry()
    stopped: list[str] = []
    mine = await reg.start("me", "collection", seed("a"), endless_worker("a", stopped))
    theirs = await reg.start(
        "them", "collection", seed("b"), endless_worker("b", stopped)
    )
    # their very first ingest, so only the server wide cap can be holding it back
    assert theirs.status == IngestStatus.QUEUED
    queued = reg.get(theirs.ingest_id, "them")
    await reg.cancel(reg.get(mine.ingest_id, "me"))
    await until(lambda: queued.snapshot().status == IngestStatus.RUNNING)
    await reg.cancel(queued)


async def test_an_owner_at_their_cap_does_not_block_another(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE", "3")
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER", "1")
    reg = registry()
    stopped: list[str] = []
    mine = await reg.start("me", "collection", seed("a"), endless_worker("a", stopped))
    blocked = await reg.start("me", "collection", seed("b"), worker_of([]))
    assert blocked.status == IngestStatus.QUEUED
    # the walk past a full owner has to skip rather than stop, or this one never starts
    theirs = await reg.start(
        "them", "collection", seed("c"), endless_worker("c", stopped)
    )
    assert theirs.status == IngestStatus.RUNNING
    await reg.cancel(reg.get(mine.ingest_id, "me"))
    await reg.cancel(reg.get(blocked.ingest_id, "me"))
    await reg.cancel(reg.get(theirs.ingest_id, "them"))


async def test_queued_ingests_start_oldest_first(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER", "1")
    reg = registry()
    stopped: list[str] = []
    first = await reg.start(
        "owner", "collection", seed("a"), endless_worker("a", stopped)
    )
    second = await reg.start(
        "owner", "collection", seed("b"), endless_worker("b", stopped)
    )
    third = await reg.start(
        "owner", "collection", seed("c"), endless_worker("c", stopped)
    )
    await reg.cancel(reg.get(first.ingest_id, "owner"))
    assert reg.get(second.ingest_id, "owner").snapshot().status == IngestStatus.RUNNING
    assert reg.get(third.ingest_id, "owner").snapshot().status == IngestStatus.QUEUED
    await reg.cancel(reg.get(second.ingest_id, "owner"))
    await reg.cancel(reg.get(third.ingest_id, "owner"))


async def test_a_queued_ingest_is_never_pruned(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER", "1")
    monkeypatch.setenv("SHABTI_INGEST_MAX_FINISHED", "0")
    monkeypatch.setenv("SHABTI_INGEST_RETENTION_SECONDS", "0")
    reg = registry()
    stopped: list[str] = []
    first = await reg.start(
        "owner", "collection", seed("a"), endless_worker("a", stopped)
    )
    second = await reg.start("owner", "collection", seed("b"), worker_of([]))
    # `list` prunes, and a queued ingest mistaken for a finished one has no `finished` timestamp to
    # beat the cutoff with, so it would be dropped right here
    listed = {item.ingest_id: item.status for item in reg.list("owner")}
    assert listed[second.ingest_id] == IngestStatus.QUEUED
    # the queued one first: cancelling the running one would promote it, and with retention zeroed
    # it would finish and be pruned before there was anything left to tidy up
    await reg.cancel(reg.get(second.ingest_id, "owner"))
    await reg.cancel(reg.get(first.ingest_id, "owner"))


async def test_cancelling_a_queued_ingest_runs_its_cleanup(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER", "1")
    reg = registry()
    stopped: list[str] = []
    ran: list[str] = []
    cleaned: list[str] = []
    first = await reg.start(
        "owner", "collection", seed("a"), endless_worker("a", stopped)
    )
    second = await reg.start(
        "owner", "collection", seed("b"), cleanup_worker("b", ran, cleaned)
    )
    final = await reg.cancel(reg.get(second.ingest_id, "owner"))
    assert final.status == IngestStatus.CANCELLED
    # the work never happened, but the worker still got to release what the POST saved
    assert ran == []
    assert cleaned == ["b"]
    await reg.cancel(reg.get(first.ingest_id, "owner"))


async def test_shutdown_cancels_queued_ingests_too(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER", "1")
    reg = registry()
    stopped: list[str] = []
    first = await reg.start(
        "owner", "collection", seed("a"), endless_worker("a", stopped)
    )
    second = await reg.start(
        "owner", "collection", seed("b"), endless_worker("b", stopped)
    )
    await reg.shutdown()
    assert reg.get(first.ingest_id, "owner").snapshot().status == IngestStatus.CANCELLED
    assert (
        reg.get(second.ingest_id, "owner").snapshot().status == IngestStatus.CANCELLED
    )


async def test_cancelling_a_collection_takes_its_queued_ingests(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER", "1")
    reg = registry()
    stopped: list[str] = []
    running = await reg.start(
        "owner", "doomed", seed("a"), endless_worker("a", stopped)
    )
    queued = await reg.start("owner", "doomed", seed("b"), worker_of([]))
    await reg.cancel_for_collection("doomed")
    assert (
        reg.get(running.ingest_id, "owner").snapshot().status == IngestStatus.CANCELLED
    )
    assert (
        reg.get(queued.ingest_id, "owner").snapshot().status == IngestStatus.CANCELLED
    )


async def test_the_stream_waits_while_the_ingest_is_queued():
    task = bare_task("a")
    stream = stream_ingest(task)
    # a queued ingest has nothing to say yet, and closing its stream would tell the client it was
    # over before it had begun
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(anext(stream), 0.05)
    task.finish(IngestStatus.CANCELLED, None)
    assert not [line async for line in stream]


async def test_finished_ingests_are_pruned_but_read_ones_are_kept(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_MAX_FINISHED", "1")
    reg = registry()
    kept = await reg.start("owner", "collection", seed("a"), worker_of([]))
    dropped = await reg.start("owner", "collection", seed("b"), worker_of([]))
    kept_task = reg.get(kept.ingest_id, "owner")
    dropped_task = reg.get(dropped.ingest_id, "owner")
    await kept_task.task
    await dropped_task.task
    # a subscriber is what keeps the older one from being pruned in favour of the newer
    kept_task.subscribe()
    assert {item.ingest_id for item in reg.list("owner")} == {kept.ingest_id}


async def test_retention_expires_a_finished_ingest(monkeypatch):
    monkeypatch.setenv("SHABTI_INGEST_RETENTION_SECONDS", "0")
    reg = registry()
    started = await reg.start("owner", "collection", seed("a"), worker_of([]))
    await reg.get(started.ingest_id, "owner").task
    assert not reg.list("owner")
