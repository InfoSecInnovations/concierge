"""Delegate to an async generator without swallowing what is thrown in.

Async generators have no delegation form: `yield from` is a `SyntaxError` inside any `async def`, so
the obvious `async for x in inner(): yield x` is all there is. It is not equivalent. Throwing into
the outer generator raises in the *outer's* frame, at its own `yield`; it leaves the `async for`, and
`async for` does not close its iterator on an exception, so `inner` is left suspended at its own
yield and is finalised later by the garbage collector with `GeneratorExit`.

That matters wherever the delegate cleans up after itself. A generator that rolls back its work in an
`except Exception` never sees the exception, and `GeneratorExit` neither reaches that handler nor
allows the `await` a rollback usually needs. `relay` iterates by hand and forwards the throw with
`athrow`, so the delegate's own handlers run in its own frame.
"""

from collections.abc import AsyncGenerator, Awaitable, Callable


async def relay[T](
    inner: AsyncGenerator[T, None],
    after: Callable[[T | None], Awaitable[None]] | None = None,
) -> AsyncGenerator[T, None]:
    """Yield everything `inner` yields, forwarding throws and closes into it.

    `after` is awaited with the last yielded value once `inner` finishes on its own, and gets `None`
    if it yielded nothing. It does not run when the stream is thrown into or closed, which is what
    lets work hang off the end of a stream without adding another frame with the same forwarding
    problem this module exists to fix.
    """
    last: T | None = None
    sent = None
    thrown: BaseException | None = None
    while True:
        try:
            if thrown is not None:
                exception, thrown = thrown, None
                # forwarded so the delegate's own handlers run in *its* frame. when it re-raises,
                # as a rollback normally does, the exception propagates from here and out of this
                # generator, which is what delegation should look like from the caller's side
                value = await inner.athrow(exception)
            else:
                value = await inner.asend(sent)
        except StopAsyncIteration:
            break
        last = value
        sent = None
        try:
            sent = yield value
        except GeneratorExit:
            # nothing may be yielded after this, so a close can only be forwarded as a close
            await inner.aclose()
            raise
        except BaseException as e:
            thrown = e
    if after is not None:
        await after(last)
