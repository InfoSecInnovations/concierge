import time
from isi_util.async_generator import asyncify_generator


def generator(start, stop):
    for i in range(start, stop):
        time.sleep(0.1)
        yield i


async def test_async_generator():
    start = 1
    stop = 5
    current = start
    async for result in asyncify_generator(generator(start, stop)):
        assert current == result
        current += 1
