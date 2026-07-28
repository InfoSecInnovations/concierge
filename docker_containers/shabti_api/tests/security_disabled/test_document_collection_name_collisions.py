from ...src.app.document_collections import (
    create_collection,
    delete_collection,
    CollectionExistsError,
)
import pytest
import secrets


async def test_collection_with_same_name():
    collection_name = secrets.token_hex(8)
    collection_info = await create_collection(None, collection_name)
    assert collection_info
    with pytest.raises(CollectionExistsError):
        await create_collection(None, collection_name)


async def test_collection_with_different_name():
    collection_name = secrets.token_hex(8)
    collection_info = await create_collection(None, collection_name)
    assert collection_info


async def test_recreate_with_same_name():
    collection_name = secrets.token_hex(8)
    collection_info = await create_collection(None, collection_name)
    assert collection_info
    await delete_collection(None, collection_info.collection_id)
    new_collection_info = await create_collection(None, collection_name)
    assert new_collection_info
