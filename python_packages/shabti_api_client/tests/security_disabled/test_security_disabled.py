from isi_util.list_util import find

collection_name = "test_collection"
collection_lookup = {}


async def test_create_collection(shabti_client):
    collection_id = await shabti_client.create_collection(collection_name)
    assert collection_id
    collection_lookup[collection_name] = collection_id


async def test_delete_collection(shabti_client):
    await shabti_client.delete_collection(collection_lookup[collection_name])
    collections = await shabti_client.get_collections()
    assert not find(
        collections, lambda x: x.collection_id == collection_lookup[collection_name]
    )
