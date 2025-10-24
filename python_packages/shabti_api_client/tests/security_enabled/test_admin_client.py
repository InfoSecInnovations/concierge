from .lib import get_client_for_user, get_admin_client

collection_name = "admin test testadmin's shared collection"
lookup = {}


async def test_can_read_collection():
    client = await get_client_for_user("testadmin")
    collection_id = await client.create_collection(collection_name, "shared")
    lookup[collection_name] = collection_id
    admin_client = await get_admin_client()
    collections = await admin_client.get_collections()
    assert len(collections)
    assert next(
        (
            collection
            for collection in collections
            if collection.collection_id == collection_id
        ),
        None,
    )


async def test_can_delete_collection():
    admin_client = await get_admin_client()
    await admin_client.delete_collection(lookup[collection_name])
    collections = await admin_client.get_collections()
    assert not any(
        collection.collection_id == lookup[collection_name]
        for collection in collections
    )
