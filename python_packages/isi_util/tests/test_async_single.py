from isi_util import async_single
import time


def long_running(add):
    time.sleep(0.5)
    return 40 + add


async def test_async_single():
    result = await async_single.asyncify(long_running, 2)
    assert result == 42
