"""Run several async generators at once under a cap, merged into one stream.

Nothing in the standard library does this: `asyncio.gather` runs coroutines that return a value, and
`TaskGroup` gives no way to read results as they arrive. Neither merges *generators*, and neither
offers what a batch of concurrent jobs needs when each one is expensive to have in flight:

- a job must not start until a slot frees, or the cap the limit exists to give is lost before the
  first value is read;
- more jobs must be submittable while the stream is being read, so work discovered by one job joins
  the same cap rather than nesting a second pool inside one occupied slot;
- one job failing must not take its siblings with it. Every ending is reported as `PoolEnded` and
  the *reader* decides what is fatal; aborting is just leaving the loop.

Stopping is the reason this is not a few lines around `asyncio.Queue`. A stop has to be *thrown
into* the running generators, at a yield, so their own `except Exception` cleanup runs in their own
frame — see `isi_util.relay`, which is what keeps that true through any wrapper. Closing them
instead would deliver `GeneratorExit`, which such a handler neither catches nor can `await` in.
Cooperative alone is not enough either, since a job is usually suspended in some long `await` rather
than at a yield, so a job that has not taken the hint within `stop_grace` is cancelled outright.

Read a pool as:

    async with pool:
        async for result in pool.results():
            ...

The context manager is what tears the survivors down when the reader leaves early; `async for` on
its own would leave that to the garbage collector.
"""

import asyncio
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass


class StreamStoppedError(Exception):
    """Thrown into a running job by `stop()`.

    An ordinary `Exception` on purpose, so a job's `except Exception` rollback catches it.
    """


@dataclass(frozen=True)
class PoolValue[T]:
    """A value yielded by the job submitted under `key`."""

    key: str
    value: T


@dataclass(frozen=True)
class PoolEnded:
    """The job submitted under `key` is over, `error` being why if it did not end on its own.

    Exactly one of these is produced for every submitted job, including one dropped by a stop
    before it ever ran, so a reader can key its own bookkeeping off this alone.
    """

    key: str
    error: BaseException | None = None


type PoolResult[T] = PoolValue[T] | PoolEnded

type JobFactory[T] = Callable[[], Awaitable[AsyncGenerator[T, None]]]


class _Wake:
    """Nudges a parked reader when a job is submitted while the pool is being read."""


_WAKE = _Wake()


@dataclass
class _Job[T]:
    key: str
    factory: JobFactory[T]
    task: asyncio.Task | None = None
    stopping: bool = False


class StreamPool[T]:
    """A bounded pool of async generators, merged into one stream of `PoolResult`."""

    def __init__(self, limit: int, stop_grace: float = 30.0) -> None:
        self._limit = limit
        self._stop_grace = stop_grace
        self._pending: deque[_Job[T]] = deque()
        self._running: dict[str, _Job[T]] = {}
        # unbounded on purpose: a job blocked on `put` could never reach the yield where it notices
        # a stop request. Volume is bounded instead by teardown awaiting the jobs before discarding
        self._queue: asyncio.Queue[PoolResult[T] | _Wake] = asyncio.Queue()
        self._keys: set[str] = set()
        self._stopping = False
        self._grace: asyncio.Task | None = None

    async def __aenter__(self) -> "StreamPool[T]":
        return self

    async def __aexit__(self, *_) -> None:
        self.stop()
        tasks = [job.task for job in self._running.values() if job.task is not None]
        if tasks:
            # waiting is the point: an aborted batch still wants its jobs to clean up after
            # themselves, and the grace task bounds how long that can take
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._grace is not None:
            self._grace.cancel()
            self._grace = None
        self._running.clear()
        self._keys.clear()
        while not self._queue.empty():
            self._queue.get_nowait()

    def submit(self, factory: JobFactory[T], key: str) -> None:
        """Queue an async callable returning a generator, to be called when a slot frees.

        A callable rather than a generator so that setup which has to `await` — a file parse, a
        crawler's start-up — happens in the slot instead of ahead of it, and without adding a
        wrapping frame that would have to forward throws itself.
        """
        if self._stopping:
            return
        if key in self._keys:
            raise ValueError(f"a job is already in the pool under key {key!r}")
        self._keys.add(key)
        self._pending.append(_Job(key=key, factory=factory))
        self._queue.put_nowait(_WAKE)

    async def results(self) -> AsyncGenerator[PoolResult[T], None]:
        """Yield every job's values and ending until nothing is left to run.

        Submitting from this loop's body is safe: the reader is suspended at its yield while the
        body runs, and emptiness is only checked after filling the free slots.
        """
        while True:
            self._fill()
            if not self._running and not self._pending and self._queue.empty():
                return
            result = await self._queue.get()
            if isinstance(result, _Wake):
                continue
            if isinstance(result, PoolEnded):
                # a job holds its slot until its ending is *read*, not until its task finishes, so
                # that "nothing is running" cannot come true while its values are still unread
                self._running.pop(result.key, None)
                self._keys.discard(result.key)
            yield result

    def stop(self) -> None:
        """Ask every running job to stop, drop the queued ones, and cancel whatever is left later.

        Cooperative first: each running job is thrown a `StreamStoppedError` at its next yield, so it
        rolls back its own work. A job that is not at a yield cannot be asked politely, so anything
        still running after `stop_grace` is cancelled — cleanup that never got its chance is the
        caller's problem to sweep up.
        """
        if self._stopping:
            return
        self._stopping = True
        while self._pending:
            dropped = self._pending.popleft()
            self._queue.put_nowait(PoolEnded(dropped.key, StreamStoppedError()))
        for job in self._running.values():
            job.stopping = True
        if self._running:
            self._grace = asyncio.create_task(self._enforce_stop())

    def _fill(self) -> None:
        while self._pending and len(self._running) < self._limit and not self._stopping:
            job = self._pending.popleft()
            self._running[job.key] = job
            job.task = asyncio.create_task(
                self._run(job), name=f"stream-pool-{job.key}"
            )

    async def _enforce_stop(self) -> None:
        await asyncio.sleep(self._stop_grace)
        for job in list(self._running.values()):
            if job.task is not None:
                job.task.cancel()

    async def _run(self, job: _Job[T]) -> None:
        error: BaseException | None = None
        try:
            if job.stopping:
                # stopped before it got a turn, so the work never starts at all
                raise StreamStoppedError()
            generator = await job.factory()
            while True:
                if job.stopping:
                    # a throw cannot be delivered while `anext` is pending — the generator is
                    # running — so the stop goes in here, at the top of the turn after it yielded
                    value = await generator.athrow(StreamStoppedError())
                else:
                    value = await anext(generator)
                self._queue.put_nowait(PoolValue(job.key, value))
        except StopAsyncIteration:
            pass
        except BaseException as e:
            error = e
        self._queue.put_nowait(PoolEnded(job.key, error))
        if isinstance(error, asyncio.CancelledError):
            raise error
