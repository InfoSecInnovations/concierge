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
    TooManyIngestsError,
)

from .ingest_events import IngestEvent, ItemFailed, ItemProgress, ItemQueued
from .loaders.base_loader import get_current_time
from .opensearch import delete_opensearch_document
from .settings import setting

type IngestWorker = Callable[
    [StreamPool[DocumentIngestInfo]], AsyncGenerator[IngestEvent, None]
]
type DocumentRemover = Callable[[str, str], Awaitable[None]]


def is_active(status: IngestStatus) -> bool:
    return status == IngestStatus.RUNNING


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
    ) -> None:
        self.ingest_id = ingest_id
        self.owner_id = owner_id
        self.collection_id = collection_id
        self.items = {item.item_id: item for item in items}
        self.pool = pool
        self.status = IngestStatus.RUNNING
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
    can be ingested before the client's follow-up request even lands.
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
            if not is_active(task.status) and not subscriber.dirty:
                return
            subscriber.event.clear()
            if not subscriber.dirty and is_active(task.status):
                await subscriber.event.wait()
    finally:
        task.unsubscribe(subscriber)


class IngestRegistry:
    """Every ingest this process is running or has recently run."""

    def __init__(self, remove_document: DocumentRemover | None = None) -> None:
        # no asyncio objects here: this is built by create_app(), before any loop is running
        self._tasks: dict[str, IngestTask] = {}
        self._remove_document = remove_document or delete_opensearch_document
        self._logger = logging.getLogger("shabti")

    async def start(
        self,
        owner_id: str,
        collection_id: str,
        items: list[IngestItemInfo],
        worker: IngestWorker,
    ) -> IngestInfo:
        self._prune()
        self._check_capacity(owner_id)
        # built here rather than inside the task, so a DELETE arriving before the task has first run
        # still has something to stop: a stopped pool never starts its queued jobs at all
        pool = StreamPool[DocumentIngestInfo](
            limit=setting("SHABTI_INGEST_CONCURRENCY"),
            stop_grace=setting("SHABTI_INGEST_STOP_GRACE_SECONDS"),
        )
        task = IngestTask(uuid4().hex, owner_id, collection_id, items, pool)
        self._tasks[task.ingest_id] = task
        task.task = asyncio.create_task(
            self._run(task, worker), name=f"ingest-{task.ingest_id}"
        )
        return task.snapshot()

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
        if task.task is not None:
            with suppress(Exception):
                await task.task
        return task.snapshot()

    async def cancel_for_collection(self, collection_id: str) -> None:
        await self._cancel_all(
            task for task in self._tasks.values() if task.collection_id == collection_id
        )

    async def shutdown(self) -> None:
        await self._cancel_all(self._tasks.values())

    async def _cancel_all(self, tasks: Iterable[IngestTask]) -> None:
        # together rather than one after another: each waits out its own stop grace, and shutdown
        # has to finish inside the container's stop timeout or the process is killed under it
        running = [task for task in list(tasks) if is_active(task.status)]
        await asyncio.gather(
            *(self.cancel(task) for task in running), return_exceptions=True
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

    def _check_capacity(self, owner_id: str) -> None:
        """Cap concurrent ingests, which nothing else does now.

        A client holding a connection open used to be the natural limit; detaching removes it, so
        without this ten POSTs and a disconnect would put MAX_ACTIVE * CONCURRENCY documents through
        the embeddings server at once.
        """
        active = [task for task in self._tasks.values() if is_active(task.status)]
        if len(active) >= setting("SHABTI_INGEST_MAX_ACTIVE"):
            raise TooManyIngestsError(
                message="Too many ingests are already running on this server"
            )
        mine = [task for task in active if task.owner_id == owner_id]
        if len(mine) >= setting("SHABTI_INGEST_MAX_ACTIVE_PER_OWNER"):
            raise TooManyIngestsError(
                message="You already have the maximum number of ingests running"
            )

    def _prune(self) -> None:
        """Forget finished ingests, oldest first, keeping any a client is still reading.

        Retaining them at all is a requirement rather than a nicety: a client that POSTs a small
        file and then asks about the ingest has to get its terminal snapshot, not a 404.
        """
        cutoff = get_current_time() - setting("SHABTI_INGEST_RETENTION_SECONDS") * 1000
        finished = [task for task in self._tasks.values() if not is_active(task.status)]
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
