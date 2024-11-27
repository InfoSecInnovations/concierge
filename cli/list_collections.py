import sys
import os
import asyncio
from .get_token import get_token

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from concierge_backend_lib.authentication import (
    get_async_result_with_token,
    get_username,
)
from concierge_backend_lib.authorization import auth_enabled
from concierge_backend_lib.document_collections import get_collections


token = get_token()


async def display_collections():
    async def do_get_collections(token):
        return await get_collections(token["access_token"])

    _, collections = await get_async_result_with_token(token, do_get_collections)
    if auth_enabled:
        for collection in collections:
            collection["owner_name"] = get_username(
                collection["attributes"]["concierge_owner"][0]
            )
    if not collections:
        print("no collections found")
    for collection in collections:
        print(f"{collection['name']}")
        if auth_enabled:
            print(
                f"{collection['type'].replace('collection:', '')} collection owned by {collection['owner_name']}"
            )
        print(f"collection ID: {collection['_id']}")
        print("")


asyncio.run(display_collections())
