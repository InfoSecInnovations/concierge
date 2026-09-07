"""Ingests that outlive the request which started them.

An ingest used to be the caller's connection: the POST held it open for the whole thing, so a
browser reload tore the ingest down and rolled the partial document back. Here it is a task this
process owns, and clients attach to it, read a snapshot plus live updates, and detach again.

Process and loop bound on purpose, which is why it lives on `app.state` rather than in a module
global - tests build an app per session, each on its own loop. Any future move to `workers > 1`
breaks re-attach outright, since an ingest would live in whichever worker took the POST.
"""

import asyncio
import logging
from collections import Counter
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass, field
from uuid import uuid4

from isi_util.stream_pool import StreamPool
from shabti_types import (
    DocumentIngestError,
    DocumentIngestInfo,
    IngestInfo,
    IngestItemInfo,
    IngestNotFoundError,
    IngestStatus,
)

from .ingest_events import IngestEvent, ItemFailed, ItemProgress, ItemQueued
from .loaders.base_loader import get_current_time
from .opensearch import delete_opensearch_document
from .settings import setting

type IngestWorker = Callable[
    [StreamPool[DocumentIngestInfo]], AsyncGenerator[IngestEvent, None]
]
type DocumentRemover = Callable[[str, str], Awaitable[None]]


def is_running(status: IngestStatus) -> bool:
    """Holding one of the concurrency slots right now."""
    return status == IngestStatus.RUNNING


def is_finished(status: IngestStatus) -> bool:
    """Over for good. Queued is neither of these: not started, and not finished either.

    Two predicates rather than three, because every site that wants "queued or running" reads
    better as `not is_finished(...)` - and getting that one wrong in `_prune` would delete an
    accepted ingest before its task even existed.
    """
    return status in (
        IngestStatus.COMPLETE,
        IngestStatus.FAILED,
        IngestStatus.CANCELLED,
    )


@dataclass
class _Subscriber:
    """One attached client's pending work.

    A dirty set rather than a queue: every event is an idempotent last-write-wins state update, so a
    stalled client holds at most one entry per item instead of an unbounded event log. Nothing can
    be missed, only coalesced, which is right for a progress display - and coalescing is safe for
    `complete` precisely because that is state rather than a delta, so the last emission carries it.
    """

    dirty: set[str] = field(default_factory=set)
    event: asyncio.Event = field(default_factory=asyncio.Event)


class IngestTask:
    def __init__(
        self,
        ingest_id: str,
        owner_id: str,
        collection_id: str,
        items: list[IngestItemInfo],
        pool: StreamPool[DocumentIngestInfo],
        worker: IngestWorker,
    ) -> None:
        self.ingest_id = ingest_id
        self.owner_id = owner_id
        self.collection_id = collection_id
        self.items = {item.item_id: item for item in items}
        self.pool = pool
        # held here rather than in a second dict keyed by id, which would have to be kept in step
        # with `_tasks` by cancellation and pruning both
        self.worker = worker
        self.status = IngestStatus.QUEUED
        # when it was submitted, not when it started: this is what orders the queue
        self.started = get_current_time()
        self.finished: int | None = None
        self.error: str | None = None
        self.cancel_requested = False
        self.task: asyncio.Task | None = None
        self._subscribers: list[_Subscriber] = []

    # everything below here is deliberately synchronous: a reader subscribes and then takes its
    # snapshot with no await in between, and state only ever changes in `apply`, which doesn't await
    # either, so no update can land in the gap and be missed by both the snapshot and the stream

    def apply(self, event: IngestEvent) -> None:
        if isinstance(event, ItemQueued):
            self.items[event.item_id] = IngestItemInfo(
                item_id=event.item_id, label=event.label
            )
        elif isinstance(event, ItemProgress):
            self._item_or_seed(event.item_id, event.info.label).info = event.info
        elif isinstance(event, ItemFailed):
            self._item_or_seed(
                event.item_id, event.error.label or ""
            ).error = event.error
        for subscriber in self._subscribers:
            subscriber.dirty.add(event.item_id)
            subscriber.event.set()

    def finish(self, status: IngestStatus, error: str | None) -> None:
        self.status = status
        self.error = error
        self.finished = get_current_time()
        # wake every reader so it notices the terminal status and ends its stream
        for subscriber in self._subscribers:
            subscriber.event.set()

    def subscribe(self) -> _Subscriber:
        subscriber = _Subscriber()
        self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: _Subscriber) -> None:
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def item(self, item_id: str) -> IngestItemInfo | None:
        item = self.items.get(item_id)
        # copied rather than handed out live: a serialisation happening after the next update would
        # otherwise ship newer state under an older line
        return item.model_copy(deep=True) if item else None

    def snapshot(self) -> IngestInfo:
        return IngestInfo(
            ingest_id=self.ingest_id,
            collection_id=self.collection_id,
            status=self.status,
            started=self.started,
            finished=self.finished,
            error=self.error,
            items=[item.model_copy(deep=True) for item in self.items.values()],
        )

    def _item_or_seed(self, item_id: str, label: str) -> IngestItemInfo:
        item = self.items.get(item_id)
        if item is None:
            item = IngestItemInfo(item_id=item_id, label=label)
            self.items[item_id] = item
        return item


def line(item: IngestItemInfo) -> DocumentIngestInfo | DocumentIngestError | None:
    """One item's state as a stream line, or nothing while it is still queued.

    Queued items stay off the stream, which is what keeps `DocumentIngestInfo.document_id` a
    required string; a client learns about them from the POST response and `GET /ingests`.
    """
    return item.error or item.info


async def stream_ingest(
    task: IngestTask,
) -> AsyncGenerator[DocumentIngestInfo | DocumentIngestError, None]:
    """The snapshot, then live updates, ending when the ingest does.

    A finished ingest streams its terminal snapshot and closes rather than erroring: a small file
    can be ingested before the client's follow-up request even lands. A queued one holds the reader
    open with nothing to say until it starts, which is why the wait is on `is_finished` rather than
    on the ingest running.
    """
    subscriber = task.subscribe()
    try:
        for item in task.snapshot().items:
            emitted = line(item)
            if emitted:
                yield emitted
        while True:
            # drained before the terminal status is checked, so an update applied while the ingest
            # was ending still gets delivered
            dirty, subscriber.dirty = subscriber.dirty, set()
            for item_id in dirty:
                item = task.item(item_id)
                emitted = line(item) if item else None
                if emitted:
                    yield emitted
            if is_finished(task.status) and not subscriber.dirty:
                return
            subscriber.event.clear()
            if not subscriber.dirty and not is_finished(task.status):
                await subscriber.event.wait()
    finally:
        task.unsubscribe(subscriber)


class IngestRegistry:
    """Every ingest this process is running, has queued, or has recently run."""

    def __init__(self, remove_document: DocumentRemover | None = None) -> None:
        # no asyncio objects here: this is built by create_app(), before any loop is running
        self._tasks: dict[str, IngestTask] = {}
        self._remove_document = remove_document or delete_opensearch_document
        self._logger = logging.getLogger("shabti")
        self._closing = False

    async def start(
        self,
        owner_id: str,
        collection_id: str,
        items: list[IngestItemInfo],
        worker: IngestWorker,
    ) -> IngestInfo:
        self._prune()
        # built here rather than inside the task, so a DELETE arriving before the task has first run
        # still has something to stop: a stopped pool never starts its queued jobs at all
        pool = StreamPool[DocumentIngestInfo](
            limit=setting("SHABTI_INGEST_CONCURRENCY"),
            stop_grace=setting("SHABTI_INGEST_STOP_GRACE_SECONDS"),
        )
        task = IngestTask(uuid4().hex, owner_id, collection_id, items, pool, worker)
        self._tasks[task.ingest_id] = task
        self._warn_if_backed_up(owner_id)
        # before the snapshot, so an ingest that has room reports itself running in the very response
        # to the POST that made it, exactly as it did before there was a queue. "queued" is only ever
        # what a client sees under load
        self._promote()
        return task.snapshot()

    def _promote(self) -> None:
        """Start whatever the caps now have room for, oldest submission first.

        A client holding a connection open used to be the natural limit on concurrency; detaching
        removed it, so without these caps ten POSTs and a disconnect would put MAX_ACTIVE *
        CONCURRENCY documents through the embeddings server at once. They bound how many ingests
        *run*, not how many may be submitted - over the cap an ingest waits rather than being
        refused, and the slot it eventually gets is handed to it by whichever ingest ended.
        """
        if self._closing:
            return
        running = [task for task in self._tasks.values() if is_running(task.status)]
        per_owner = Counter(task.owner_id for task in running)
        free = setting("SHABTI_INGEST_MAX_ACTIVE") - len(running)
        # `started` is milliseconds, so simultaneous submissions tie - a stable sort over a dict
        # that is already in insertion order breaks those ties on arrival
        queued = sorted(
            (
                task
                for task in self._tasks.values()
                if task.status == IngestStatus.QUEUED
            ),
            key=lambda task: task.started,
        )
        for task in queued:
            if free <= 0:
                return
            if per_owner[task.owner_id] >= setting(
                "SHABTI_INGEST_MAX_ACTIVE_PER_OWNER"
            ):
                # skipped rather than returned on, or one owner sitting at their own cap would stall
                # everybody queued behind them
                continue
            self._begin(task)
            per_owner[task.owner_id] += 1
            free -= 1

    def _begin(self, task: IngestTask) -> None:
        """Give a queued ingest its slot. The only place an ingest's task is created.

        The status flip and the create_task happen in the same turn with nothing awaited between
        them, which is the whole interlock: nothing else can pick a task up once it has stopped
        being queued.
        """
        task.status = IngestStatus.RUNNING
        task.task = asyncio.create_task(
            self._run(task, task.worker), name=f"ingest-{task.ingest_id}"
        )

    def _warn_if_backed_up(self, owner_id: str) -> None:
        """Say something before the disk does.

        Nothing bounds the queue now that a submission is never refused, and a queued files ingest
        pins the binaries the POST saved for as long as it waits. If this ever needs a real limit it
        wants to be a per-owner staged-byte quota, not a rejection.
        """
        depth = len(
            [
                task
                for task in self._tasks.values()
                if task.status == IngestStatus.QUEUED and task.owner_id == owner_id
            ]
        )
        if depth >= setting("SHABTI_INGEST_QUEUE_WARN_DEPTH"):
            self._logger.warning(
                "owner %s has %s ingests queued, holding their uploads on disk",
                owner_id,
                depth,
            )

    def list(self, owner_id: str) -> list[IngestInfo]:
        self._prune()
        return [
            task.snapshot()
            for task in self._tasks.values()
            if task.owner_id == owner_id
        ]

    def get(self, ingest_id: str, owner_id: str) -> IngestTask:
        self._prune()
        task = self._tasks.get(ingest_id)
        # a foreign id is reported exactly like a missing one, so ids aren't enumerable
        if task is None or task.owner_id != owner_id:
            raise IngestNotFoundError(
                ingest_id=ingest_id, message=f"No ingest with ID {ingest_id}"
            )
        return task

    async def cancel(self, task: IngestTask) -> IngestInfo:
        """Stop an ingest and wait for it to unwind.

        The pool is stopped rather than the asyncio task cancelled, so each job is thrown an
        ordinary exception at its next yield and rolls its own document back in its own frame.
        Whatever cannot be asked politely the pool cancels after its grace period, and the sweep in
        `_run` is the backstop for the documents that leaves behind.
        """
        task.cancel_requested = True
        task.pool.stop()
        if task.task is None:
            # a queued ingest still has cleaning up to do - a files ingest's binaries were written to
            # disk by the POST - and its worker is the only thing that knows what. Run against a
            # stopped pool it submits nothing, reads an empty stream and falls straight into its own
            # cleanup, so a queued ingest unwinds down exactly the path a running one does. Started
            # regardless of the caps: it does no work, and waiting for a slot would hang the DELETE
            self._begin(task)
        if task.task is not None:
            with suppress(Exception):
                await task.task
        return task.snapshot()

    async def cancel_for_collection(self, collection_id: str) -> None:
        await self._cancel_all(
            task for task in self._tasks.values() if task.collection_id == collection_id
        )

    async def shutdown(self) -> None:
        # nothing queued should be promoted into a container that is stopping, and an ingest ending
        # under us would otherwise do exactly that. `cancel_for_collection` deliberately doesn't
        self._closing = True
        await self._cancel_all(self._tasks.values())

    async def _cancel_all(self, tasks: Iterable[IngestTask]) -> None:
        # together rather than one after another: each waits out its own stop grace, and shutdown
        # has to finish inside the container's stop timeout or the process is killed under it
        unfinished = [task for task in list(tasks) if not is_finished(task.status)]
        await asyncio.gather(
            *(self.cancel(task) for task in unfinished), return_exceptions=True
        )

    async def _run(self, task: IngestTask, worker: IngestWorker) -> None:
        status = IngestStatus.COMPLETE
        error: str | None = None
        try:
            async for event in worker(task.pool):
                task.apply(event)
        except Exception as e:
            # nobody awaits this task, so what used to become an HTTP response is now the ingest's
            # terminal status, with the traceback logged
            status = IngestStatus.FAILED
            error = f"{type(e).__name__}: {e}"
            self._logger.exception("ingest %s failed", task.ingest_id)
        finally:
            await self._sweep(task)
            if task.cancel_requested:
                status = IngestStatus.CANCELLED
            task.finish(status, error)
            # after the status is terminal, or this ingest is still counted against the very cap it
            # is trying to hand on
            self._promote()

    async def _sweep(self, task: IngestTask) -> None:
        """Delete any document an interrupted ingest left half written.

        A job asked to stop at a yield rolls itself back, but one stuck somewhere it could not be
        asked was cancelled outright, and cancellation skips that rollback. The snapshot already
        knows which documents those are - the ones with an id and no completion - so this covers a
        rollback that failed on its own as well.
        """
        for item in task.items.values():
            if item.info and not item.info.complete:
                with suppress(Exception):
                    await self._remove_document(
                        task.collection_id, item.info.document_id
                    )

    def _prune(self) -> None:
        """Forget finished ingests, oldest first, keeping any a client is still reading.

        Retaining them at all is a requirement rather than a nicety: a client that POSTs a small
        file and then asks about the ingest has to get its terminal snapshot, not a 404.
        """
        cutoff = get_current_time() - setting("SHABTI_INGEST_RETENTION_SECONDS") * 1000
        # `is_finished` rather than "not running": a queued ingest counted as finished would have
        # `finished or 0` of 0, which is under any cutoff, so it would be dropped on the very next
        # `list()` - an accepted ingest lost before its task even existed
        finished = [task for task in self._tasks.values() if is_finished(task.status)]
        prunable = sorted(
            (task for task in finished if not task.subscriber_count),
            key=lambda task: task.finished or 0,
        )
        # counted against every finished ingest rather than only the droppable ones, so one being
        # read doesn't stop an older one going when the cap is reached
        excess = len(finished) - setting("SHABTI_INGEST_MAX_FINISHED")
        for index, task in enumerate(prunable):
            if index < excess or (task.finished or 0) <= cutoff:
                del self._tasks[task.ingest_id]
