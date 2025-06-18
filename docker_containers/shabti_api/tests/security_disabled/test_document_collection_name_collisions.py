from ...src.app.document_collections import (
    create_collection,
    delete_collection,
    CollectionExistsError,
)
import pytest
import asyncio

collection_ids = []


async def test_collection_with_same_name():
    collection_id = await create_collection(None, "collection_1")
    collection_ids.append(collection_id)
    with pytest.raises(CollectionExistsError):
        collection_id = await create_collection(None, "collection_1")
        collection_ids.append(collection_id)


async def test_collection_with_different_name():
    collection_id = await create_collection(None, "collection_2")
    collection_ids.append(collection_id)
    assert collection_id


async def clean_up_collections():
    for id in collection_ids:
        # the tests may have deleted some of these, so we allow exceptions here
        try:
            await delete_collection(None, id)
        except Exception:
            pass


def teardown_module():
    asyncio.run(clean_up_collections())
