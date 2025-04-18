# This test should be run once Concierge is installed with the demo RBAC configuration
# For best results it should be fresh installation with no collections created or tweaks made to the access controls
# Do not use this on a production instance!

from .lib import create_collection_for_user, clean_up_collections
import asyncio
import pytest
from concierge_types import CollectionExistsError


async def test_own_private_collection_with_same_name():
    await create_collection_for_user("testadmin", "private", "1")
    with pytest.raises(CollectionExistsError):
        await create_collection_for_user("testadmin", "private", "1")


async def test_private_collection_with_different_name():
    collection_id = await create_collection_for_user("testadmin", "private", "2")
    assert collection_id


async def test_shared_collection_with_existing_private_name():
    collection_id = await create_collection_for_user("testadmin", "shared", "1")
    assert collection_id


async def test_shared_collection_with_existing_name():
    with pytest.raises(CollectionExistsError):
        await create_collection_for_user("testadmin", "shared", "1")


async def test_shared_collection_with_existing_name_and_different_user():
    with pytest.raises(CollectionExistsError):
        await create_collection_for_user("testshared", "shared", "1")


async def test_private_collection_with_existing_name_and_different_user():
    collection_id = await create_collection_for_user("testprivate", "private", "1")
    assert collection_id


def teardown_module():
    asyncio.run(clean_up_collections())
