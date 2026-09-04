import contextlib
import pytest
from isi_util.relay import relay


class StopError(Exception):
    """stands in for a cooperative stop thrown into a stream that has work to roll back"""


class Recorder:
    """what a delegate's own handlers observed, which is the whole point of the exercise"""

    def __init__(self):
        self.saw: BaseException | None = None
        self.rolled_back = False
        self.finalised = False


def counter(recorder: Recorder, count: int = 5):
    async def inner():
        try:
            for i in range(count):
                yield i
        except Exception as e:
            recorder.saw = e
            recorder.rolled_back = True
            raise
        finally:
            recorder.finalised = True

    return inner()


def record(seen: list):
    async def after(last):
        seen.append(last)

    return after


async def test_a_throw_reaches_the_delegate():
    recorder = Recorder()
    stop = StopError()
    stream = relay(counter(recorder))

    assert await anext(stream) == 0
    with pytest.raises(StopError) as raised:
        await stream.athrow(stop)

    assert raised.value is stop
    assert recorder.saw is stop
    assert recorder.rolled_back
    assert recorder.finalised


async def test_naive_delegation_does_not_reach_the_delegate():
    """The reason this module exists. `async for` leaves the delegate suspended and unaware."""
    recorder = Recorder()

    async def naive():
        async for value in counter(recorder):
            yield value

    stream = naive()
    assert await anext(stream) == 0
    with pytest.raises(StopError):
        await stream.athrow(StopError())

    assert recorder.saw is None
    assert not recorder.rolled_back
    assert not recorder.finalised


async def test_a_throw_reaches_the_innermost_of_a_chain():
    recorder = Recorder()
    seen = []
    stream = relay(relay(counter(recorder), after=record(seen)), after=record(seen))

    assert await anext(stream) == 0
    with pytest.raises(StopError):
        await stream.athrow(StopError())

    assert recorder.rolled_back
    assert seen == []


async def test_values_relay_in_order_and_after_gets_the_last():
    recorder = Recorder()
    seen = []

    values = [value async for value in relay(counter(recorder, 3), after=record(seen))]

    assert values == [0, 1, 2]
    assert seen == [2]
    assert recorder.finalised


async def test_after_receives_none_for_an_empty_stream():
    async def empty():
        for _ in ():
            yield

    seen = []
    assert [value async for value in relay(empty(), after=record(seen))] == []
    assert seen == [None]


async def test_after_does_not_run_on_a_throw():
    seen = []
    stream = relay(counter(Recorder()), after=record(seen))

    assert await anext(stream) == 0
    with pytest.raises(StopError):
        await stream.athrow(StopError())

    assert seen == []


async def test_closing_forwards_and_skips_after():
    recorder = Recorder()
    seen = []
    stream = relay(counter(recorder), after=record(seen))

    assert await anext(stream) == 0
    await stream.aclose()

    assert recorder.finalised
    # GeneratorExit is not an Exception, so a close is not a failure the delegate rolls back from
    assert not recorder.rolled_back
    assert seen == []


async def test_breaking_under_aclosing_forwards():
    recorder = Recorder()

    # a bare `break` leaves finalisation to the loop's async generator hooks, so the close has to
    # be asked for to be observable here
    async with contextlib.aclosing(relay(counter(recorder))) as stream:
        async for _ in stream:
            break

    assert recorder.finalised


async def test_an_exception_from_the_delegate_propagates():
    async def boom():
        yield 0
        raise ValueError("boom")

    seen = []
    with pytest.raises(ValueError, match="boom"):
        async for _ in relay(boom(), after=record(seen)):
            pass

    assert seen == []


async def test_an_absorbed_throw_keeps_relaying():
    absorbed = []

    async def tolerant():
        for i in range(4):
            try:
                yield i
            except StopError:
                absorbed.append(i)

    stream = relay(tolerant())
    assert await anext(stream) == 0
    assert await stream.athrow(StopError()) == 1
    assert await anext(stream) == 2
    await stream.aclose()

    assert absorbed == [0]


async def test_a_sent_value_reaches_the_delegate():
    async def echo():
        sent = yield "first"
        yield f"echo:{sent}"

    stream = relay(echo())
    assert await anext(stream) == "first"
    assert await stream.asend("hello") == "echo:hello"
    await stream.aclose()
