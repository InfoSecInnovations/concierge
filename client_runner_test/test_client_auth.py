from concierge_api_client.auth_client import ConciergeAuthorizationClient
import asyncio
from concierge_scripts.load_dotenv import load_env
import ssl
import os
from docker_containers.concierge_api.app.authentication import get_keycloak_client

load_env()

keycloak_client = get_keycloak_client()
token = keycloak_client.token("testshared", "test")

client = ConciergeAuthorizationClient(
    server_url="http://127.0.0.1:8000",
    verify=ssl.create_default_context(cafile=os.getenv("ROOT_CA")),
    keycloak_client=keycloak_client,
    token=token,
)


async def test_collection_create():
    collection_id = await client.create_collection("stlbl", "private")
    print(collection_id)


asyncio.run(test_collection_create())
