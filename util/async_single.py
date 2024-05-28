import concurrent.futures
import asyncio


async def asyncify(func, *args, **kwargs):
    pool = concurrent.futures.ThreadPoolExecutor()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(pool, func, *args, **kwargs)
    pool.shutdown()
    return result
