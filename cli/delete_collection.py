import sys
import os
from .get_token import get_token

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from concierge_backend_lib.document_collections import delete_collection
from concierge_backend_lib.authentication import execute_async_with_token
import asyncio

parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="Collection ID of the collection to be deleted.",
)
args = parser.parse_args()

collection_id = args.collection
token = get_token()


async def delete_selected_collection():
    async def do_delete(token):
        await delete_collection(token["access_token"], collection_id)

    await execute_async_with_token(token, do_delete)


asyncio.run(delete_selected_collection())
