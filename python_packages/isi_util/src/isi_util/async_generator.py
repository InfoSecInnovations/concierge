import concurrent.futures
import asyncio


async def asyncify_generator(gen):
    pool = concurrent.futures.ThreadPoolExecutor()
    loop = asyncio.get_event_loop()

    def wrapped():
        for x in gen:
            yield x
        raise StopAsyncIteration

    iter = wrapped()

    while True:
        try:
            x = await loop.run_in_executor(pool, next, iter)
            yield x
        except StopAsyncIteration:
            pool.shutdown()
            return
