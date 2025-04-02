from concierge_api_client.client import ConciergeClient
import asyncio

client = ConciergeClient(server_url="http://127.0.0.1:8000")


async def test_collection_create():
    collection_id = await client.create_collection("stlbl")
    print(collection_id)


asyncio.run(test_collection_create())
