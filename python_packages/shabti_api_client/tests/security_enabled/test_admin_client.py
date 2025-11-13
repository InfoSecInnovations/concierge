from .lib import get_admin_client
import pytest


@pytest.mark.parametrize(
    "shabti_collection_id",
    [
        ({"username": "testadmin", "location": "private"}),
    ],
    indirect=True,
)
async def test_can_read_collection(shabti_collection_id):
    admin_client = await get_admin_client()
    collections = await admin_client.get_collections()
    assert len(collections)
    assert next(
        (
            collection
            for collection in collections
            if collection.collection_id == shabti_collection_id
        ),
        None,
    )


@pytest.mark.parametrize(
    "shabti_collection_id",
    [
        ({"username": "testadmin", "location": "private"}),
    ],
    indirect=True,
)
async def test_can_delete_collection(shabti_collection_id):
    admin_client = await get_admin_client()
    await admin_client.delete_collection(shabti_collection_id)
    collections = await admin_client.get_collections()
    assert not any(
        collection.collection_id == shabti_collection_id for collection in collections
    )
