import pytest

# The module is currently skipped because there's a conflict somewhere between Playwright and one of the other dependencies.
# We believe it's some sort of incompatibility between pytest-asyncio and Playwright, but we needed to press on with other features so for now this has been put to one side.
# We welcome contributions on GitHub to attempt to remove the errors on teardown.
# It may be possible to use anyio instead of pytest-asyncio but we haven't investigated this path properly.

pytest.skip("Testing using Shiny causes errors on teardown", allow_module_level=True)
