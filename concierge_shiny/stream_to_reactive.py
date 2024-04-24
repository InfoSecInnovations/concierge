# Taken from https://github.com/wch/chatstream/blob/a2a1e41354cd811f5eedaabbb728e46324689abb/chatstream/__init__.py#L510-L571
# not in use yet, but it should be possible to make a chat message stream with this

from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Coroutine,
    Generic,
    TypeVar,
    cast,
)
import inspect
import time
import asyncio
from shiny import reactive
T = TypeVar("T")

# A place to keep references to Tasks so they don't get GC'd prematurely, as directed in
# asyncio.create_task docs
running_tasks: set[asyncio.Task[Any]] = set()

def safe_create_task(task: Coroutine[Any, Any, T]) -> asyncio.Task[T]:
    t = asyncio.create_task(task)
    running_tasks.add(t)
    t.add_done_callback(running_tasks.remove)
    return t

class StreamResult(Generic[T]):
    _read: Callable[[], tuple[T, ...]]
    _cancel: Callable[[], bool]

    def __init__(self, read: Callable[[], tuple[T, ...]], cancel: Callable[[], bool]):
        self._read = read
        self._cancel = cancel

    def __call__(self) -> tuple[T, ...]:
        """
        Perform a reactive read of the stream. You'll get the latest value, and you will
        receive an invalidation if a new value becomes available.
        """

        return self._read()

    def cancel(self) -> bool:
        """
        Stop the underlying stream from being consumed. Returns False if the task is
        already done or cancelled.
        """
        return self._cancel()


# Converts an async generator of type T into a reactive source of type tuple[T, ...].
def stream_to_reactive(
    func: AsyncGenerator[T, None] | Awaitable[AsyncGenerator[T, None]],
    throttle: float = 0,
) -> StreamResult[T]:
    val: reactive.Value[tuple[T, ...]] = reactive.Value(tuple())

    async def task_main():
        nonlocal func
        if inspect.isawaitable(func):
            func = await func  # type: ignore
        func = cast(AsyncGenerator[T, None], func)

        last_message_time = time.time()
        message_batch: list[T] = []

        async for message in func:
            # This print will display every message coming from the server.
            # print(json.dumps(message, indent=2))
            message_batch.append(message)

            if time.time() - last_message_time > throttle:
                async with reactive.lock():
                    val.set(tuple(message_batch))
                    await reactive.flush()

                last_message_time = time.time()
                message_batch = []

        # Once the stream has ended, flush the remaining messages.
        if len(message_batch) > 0:
            async with reactive.lock():
                val.set(tuple(message_batch))
                await reactive.flush()

    task = safe_create_task(task_main())

    return StreamResult(val.get, lambda: task.cancel())