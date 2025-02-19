import nest_asyncio


def pytest_configure():
    nest_asyncio.apply()
