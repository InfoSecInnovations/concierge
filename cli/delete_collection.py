import sys
import os
from get_token import get_token

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from concierge_backend_lib.document_collections import delete_collection
import asyncio
from concierge_scripts.load_dotenv import load_env

load_env()

parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="Collection ID of the collection to be deleted.",
)
args = parser.parse_args()

collection_id = args.collection

asyncio.run(delete_collection(get_token()["access_token"], collection_id))
