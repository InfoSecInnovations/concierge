import asyncio
import itertools
import pytest
from isi_util.relay import relay
from isi_util.stream_pool import PoolEnded, PoolValue, StreamPool, StreamStoppedError


class Recorder:
    """what a job's own handlers observed, standing in for work it would roll back"""

    def __init__(self):
        self.saw: BaseException | None = None
        self.rolled_back = False
        self.finalised = False


class Tracker:
    """how many jobs were alive at once, which is the whole point of the limit"""

    def __init__(self):
        self.live = 0
        self.peak = 0

    def enter(self):
        self.live += 1
        self.peak = max(self.peak, self.live)

    def leave(self):
        self.live -= 1


def job(key, values=(0, 1, 2), *, recorder=None, tracker=None, started=None, tail=None):
    """a factory for a job yielding `values`, then awaiting `tail` if there is one

    It awaits between values so that jobs sharing the pool can actually interleave — a generator
    that never awaits would run to completion inside a single turn of the event loop.
    """

    async def run():
        if tracker is not None:
            tracker.enter()
        try:
            for value in values:
                await asyncio.sleep(0)
                yield value
            if tail is not None:
                await tail()
        except Exception as e:
            if recorder is not None:
                recorder.saw = e
                recorder.rolled_back = True
            raise
        finally:
            if recorder is not None:
                recorder.finalised = True
            if tracker is not None:
                tracker.leave()

    async def factory():
        if started is not None:
            started.append(key)
        return run()

    return factory


def raiser(error):
    async def tail():
        raise error

    return tail


async def drain(pool):
    async with pool:
        return [result async for result in pool.results()]


def values_of(results, key):
    return [r.value for r in results if isinstance(r, PoolValue) and r.key == key]


def endings(results):
    return {r.key: r for r in results if isinstance(r, PoolEnded)}


async def test_values_and_endings_carry_their_key():
    pool = StreamPool(limit=2)
    pool.submit(job("a", [0, 1]), key="a")
    pool.submit(job("b", ["x"]), key="b")

    results = await drain(pool)

    assert values_of(results, "a") == [0, 1]
    assert values_of(results, "b") == ["x"]
    assert endings(results) == {"a": PoolEnded("a"), "b": PoolEnded("b")}
    # a job's ending comes after everything it yielded
    assert results.index(PoolEnded("a")) > results.index(PoolValue("a", 1))


async def test_concurrency_never_exceeds_the_limit():
    tracker = Tracker()
    pool = StreamPool(limit=2)
    for key in "abcd":
        pool.submit(job(key, tracker=tracker), key=key)

    results = await drain(pool)

    assert tracker.peak == 2
    assert tracker.live == 0
    assert set(endings(results)) == set("abcd")
    assert all(values_of(results, key) == [0, 1, 2] for key in "abcd")


async def test_a_job_does_not_start_before_its_slot_frees():
    started = []
    pool = StreamPool(limit=1)
    for key in "abc":
        pool.submit(job(key, started=started), key=key)

    async with pool:
        stream = pool.results()
        assert await anext(stream) == PoolValue("a", 0)
        # the Tika parse of b, and of c, has not been paid for yet
        assert started == ["a"]
        rest = [result async for result in stream]

    assert started == ["a", "b", "c"]
    assert set(endings(rest)) == set("abc")


async def test_jobs_interleave_rather_than_run_one_after_another():
    pool = StreamPool(limit=2)
    pool.submit(job("a"), key="a")
    pool.submit(job("b"), key="b")

    results = await drain(pool)
    seen = [r.key for r in results if isinstance(r, PoolValue)]

    assert seen == ["a", "b", "a", "b", "a", "b"]


async def test_the_reader_can_submit_while_reading():
    """the zip shape: a job's failure is what reveals the work hiding inside it"""
    started = []
    pool = StreamPool(limit=1)
    pool.submit(
        job("archive", [0], started=started, tail=raiser(ValueError("zip"))),
        key="archive",
    )

    results = []
    async with pool:
        async for result in pool.results():
            results.append(result)
            if isinstance(result, PoolEnded) and result.key == "archive":
                pool.submit(job("member", [7], started=started), key="member")

    assert started == ["archive", "member"]
    assert values_of(results, "member") == [7]
    assert endings(results)["member"].error is None


async def test_a_running_job_can_submit_and_it_starts_promptly():
    started = []
    pool = StreamPool(limit=3)

    async def submitter():
        pool.submit(job("spawned", [1], started=started), key="spawned")
        yield "submitted"
        # long enough that the spawned job could only be seen first if it started immediately
        for _ in range(10):
            await asyncio.sleep(0)
        yield "done"

    async def factory():
        started.append("parent")
        return submitter()

    pool.submit(factory, key="parent")
    results = await drain(pool)
    keys = [r.key for r in results if isinstance(r, PoolValue)]

    assert started == ["parent", "spawned"]
    assert keys.index("spawned") < keys.index("parent", 1)


async def test_a_failing_job_does_not_take_its_siblings_with_it():
    error = ValueError("boom")
    recorder = Recorder()
    pool = StreamPool(limit=2)
    pool.submit(job("bad", [0], recorder=recorder, tail=raiser(error)), key="bad")
    pool.submit(job("good"), key="good")

    results = await drain(pool)

    assert endings(results)["bad"].error is error
    assert recorder.rolled_back
    assert values_of(results, "bad") == [0]
    assert values_of(results, "good") == [0, 1, 2]
    assert endings(results)["good"].error is None


async def test_a_factory_that_raises_is_reported_the_same_way():
    error = RuntimeError("could not be loaded")

    async def factory():
        raise error

    pool = StreamPool(limit=2)
    pool.submit(factory, key="unloadable")
    pool.submit(job("good", [0]), key="good")

    results = await drain(pool)

    assert endings(results)["unloadable"].error is error
    assert values_of(results, "good") == [0]


async def test_the_reader_leaving_tears_the_survivors_down():
    started = []
    recorders = {key: Recorder() for key in "abc"}
    pool = StreamPool(limit=2, stop_grace=0.1)
    for key in "abc":
        pool.submit(
            job(key, itertools.count(), recorder=recorders[key], started=started),
            key=key,
        )

    async with pool:
        async for _ in pool.results():
            break

    assert started == ["a", "b"]
    for key in "ab":
        assert isinstance(recorders[key].saw, StreamStoppedError)
        assert recorders[key].rolled_back
        assert recorders[key].finalised
    assert not recorders["c"].finalised


async def test_a_stop_reaches_the_innermost_generator_of_a_relay_chain():
    """the reason `relay` exists: a wrapped job still gets to roll its own work back"""
    recorder = Recorder()

    inner = job("wrapped", itertools.count(), recorder=recorder)

    async def factory():
        return relay(relay(await inner()))

    pool = StreamPool(limit=1, stop_grace=1)
    pool.submit(factory, key="wrapped")

    results = []
    async with pool:
        stream = pool.results()
        assert await anext(stream) == PoolValue("wrapped", 0)
        pool.stop()
        results = [result async for result in stream]

    assert isinstance(recorder.saw, StreamStoppedError)
    assert recorder.rolled_back
    assert recorder.finalised
    assert isinstance(endings(results)["wrapped"].error, StreamStoppedError)


async def test_a_stop_drops_the_queued_jobs():
    started = []
    pool = StreamPool(limit=1, stop_grace=1)
    for key in "abc":
        pool.submit(job(key, itertools.count(), started=started), key=key)

    async with pool:
        stream = pool.results()
        assert await anext(stream) == PoolValue("a", 0)
        pool.stop()
        ended = endings([result async for result in stream])

    assert started == ["a"]
    # every submitted job reports an ending, so nothing seeded is left in limbo
    assert set(ended) == set("abc")
    assert all(isinstance(ended[key].error, StreamStoppedError) for key in "abc")


async def test_a_job_that_cannot_take_the_hint_is_cancelled_after_the_grace():
    recorder = Recorder()
    pool = StreamPool(limit=1, stop_grace=0.05)
    # blocks somewhere that is not a yield, as an embeddings call or a crawl page does
    pool.submit(
        job("stuck", [0], recorder=recorder, tail=lambda: asyncio.sleep(30)),
        key="stuck",
    )

    async with pool:
        stream = pool.results()
        assert await anext(stream) == PoolValue("stuck", 0)
        pool.stop()
        async with asyncio.timeout(5):
            ending = await anext(stream)

    assert isinstance(ending.error, asyncio.CancelledError)
    # cancellation is not an Exception, so the job's own rollback never ran — that is the gap a
    # caller has to sweep up itself, and why the cooperative attempt comes first
    assert not recorder.rolled_back
    assert recorder.finalised


async def test_an_empty_pool_ends_immediately():
    assert await drain(StreamPool(limit=2)) == []


async def test_submitting_after_a_stop_is_ignored():
    started = []
    pool = StreamPool(limit=2)
    pool.stop()
    pool.submit(job("late", started=started), key="late")

    assert await drain(pool) == []
    assert started == []


async def test_a_duplicate_key_is_refused():
    pool = StreamPool(limit=2)
    pool.submit(job("a"), key="a")

    with pytest.raises(ValueError, match="'a'"):
        pool.submit(job("a"), key="a")

    async with pool:
        assert set(endings([result async for result in pool.results()])) == {"a"}
