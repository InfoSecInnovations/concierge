from isi_util.list_util import find
import os

collection_name = "test_collection"
collection_lookup = {}
document_id = None

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


async def test_create_collection(shabti_client):
    collection_id = await shabti_client.create_collection(collection_name)
    assert collection_id
    collection_lookup[collection_name] = collection_id


async def test_list_collections(shabti_client):
    collections = await shabti_client.get_collections()
    assert find(
        collections, lambda x: x.collection_id == collection_lookup[collection_name]
    )


async def test_ingest_document(shabti_client):
    global document_id
    async for info in shabti_client.insert_files(
        collection_lookup[collection_name], [file_path]
    ):
        document_id = info.document_id
    assert document_id


async def test_delete_collection(shabti_client):
    await shabti_client.delete_collection(collection_lookup[collection_name])
    collections = await shabti_client.get_collections()
    assert not find(
        collections, lambda x: x.collection_id == collection_lookup[collection_name]
    )
