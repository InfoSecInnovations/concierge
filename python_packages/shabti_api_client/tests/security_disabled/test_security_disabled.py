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
    assert next(
        (
            collection
            for collection in collections
            if collection.collection_id == collection_lookup[collection_name]
        ),
        None,
    )


async def test_ingest_document(shabti_client):
    global document_id
    async for info in shabti_client.insert_files(
        collection_lookup[collection_name], [file_path]
    ):
        document_id = info.document_id
    assert document_id


async def test_ingest_url(shabti_client):
    url_document_id = None
    async for info in shabti_client.insert_urls(
        collection_lookup[collection_name], ["https://example.com/"]
    ):
        url_document_id = info.document_id
    assert url_document_id


async def test_list_documents(shabti_client):
    docs = await shabti_client.get_documents(collection_lookup[collection_name])
    assert next((doc for doc in docs if doc.document_id == document_id), None)


async def test_delete_document(shabti_client):
    await shabti_client.delete_document(collection_lookup[collection_name], document_id)
    docs = await shabti_client.get_documents(collection_lookup[collection_name])
    assert not any(doc.document_id == document_id for doc in docs)


async def test_delete_collection(shabti_client):
    await shabti_client.delete_collection(collection_lookup[collection_name])
    collections = await shabti_client.get_collections()
    assert not any(
        collection.collection_id == collection_lookup[collection_name]
        for collection in collections
    )
