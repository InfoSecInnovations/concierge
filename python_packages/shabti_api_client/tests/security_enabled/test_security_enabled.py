import os
import pytest
from .lib import get_client_for_user, get_admin_client
import asyncio
from shabti_api_client import ShabtiAuthenticationError

collection_lookup = {}

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


@pytest.mark.parametrize(
    "user,location",
    [
        ("testadmin", "private"),
        ("testadmin", "shared"),
        ("testshared", "shared"),
        ("testprivate", "private"),
    ],
)
async def test_can_create_collection(user, location):
    client = await get_client_for_user(user)
    collection_name = f"{user}'s {location} collection"
    collection_id = await client.create_collection(collection_name, location)
    assert collection_id
    collection_lookup[collection_name] = collection_id


@pytest.mark.parametrize(
    "user,location",
    [
        ("testshared", "private"),
        ("testprivate", "shared"),
        ("testsharedread", "private"),
        ("testsharedread", "shared"),
        ("testnothing", "private"),
        ("testnothing", "shared"),
    ],
)
async def test_cannot_create_collection(user, location):
    with pytest.raises(ShabtiAuthenticationError):
        client = await get_client_for_user(user)
        collection_name = f"{user}'s {location} collection"
        await client.create_collection(collection_name, location)


async def clean_up_collections():
    client = await get_admin_client()
    for id in collection_lookup.values():
        # the tests may have deleted some of these, so we allow exceptions here
        try:
            await client.delete_collection(id)
        except Exception:
            pass


def teardown_module():
    asyncio.run(clean_up_collections())
