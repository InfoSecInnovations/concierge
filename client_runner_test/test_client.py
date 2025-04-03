from concierge_api_client.client import ConciergeClient
import asyncio
import os

client = ConciergeClient(server_url="http://127.0.0.1:8000")
collection_id = None

filename = "test_doc.txt"
file_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "docker_containers",
    "concierge_api",
    "tests",
    "assets",
    filename,
)


async def test_collection_create():
    global collection_id
    collection_id = await client.create_collection("stlbl")
    print(collection_id)


async def test_list_collections():
    collections = await client.get_collections()
    print(collections)


async def test_insert_document():
    async for line in client.insert_files(collection_id, [file_path]):
        print(line)


async def test_collection_delete():
    deleted_collection_id = await client.delete_collection(collection_id)
    print(deleted_collection_id)


async def run_all():
    await test_collection_create()
    await test_list_collections()
    await test_insert_document()
    await test_collection_delete()


asyncio.run(run_all())
