import sys
import os
import asyncio

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from concierge_backend_lib.authentication import (
    get_keycloak_client,
    get_keycloak_admin_openid_token,
    get_async_result_with_token,
)
from concierge_backend_lib.document_collections import get_collections

client = get_keycloak_client()
token = get_keycloak_admin_openid_token(client)


async def display_collections():
    async def do_get_collections(token):
        return await get_collections(token["access_token"])

    _, collections = await get_async_result_with_token(token, do_get_collections)
    for collection_name in collections:
        print(collection_name)


asyncio.run(display_collections())
