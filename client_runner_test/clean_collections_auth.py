from concierge_api_client.auth_client import ConciergeAuthorizationClient
from docker_containers.concierge_api.app.authentication import get_keycloak_client
from concierge_scripts.load_dotenv import load_env
import asyncio
import os
import ssl

load_env()

keycloak_client = get_keycloak_client()
token = keycloak_client.token("testadmin", "test")

client = ConciergeAuthorizationClient(
    server_url="http://127.0.0.1:8000",
    verify=ssl.create_default_context(cafile=os.getenv("ROOT_CA")),
    keycloak_client=keycloak_client,
    token=token,
)


async def delete_collections():
    collections = await client.get_collections()
    for collection in collections:
        await client.delete_collection(collection.collection_id)


asyncio.run(delete_collections())
