import pytest
import os
from isi_util.list_util import find
from shabti_api_client import ShabtiClient

if os.getenv("SHABTI_SECURITY_ENABLED") == "True":
    pytest.skip(reason="security not enabled", allow_module_level=True)

client = ShabtiClient("http://localhost:15131")
collection_name = "test_collection"
collection_lookup = {}


async def test_create_collection():
    collection_id = await client.create_collection(collection_name)
    assert collection_id
    collection_lookup[collection_name] = collection_id


async def test_delete_collection():
    await client.delete_collection(collection_lookup[collection_name])
    collections = await client.get_collections
    assert not find(
        collections, lambda x: x.collection_id == collection_lookup[collection_name]
    )
