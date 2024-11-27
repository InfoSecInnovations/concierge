import sys
import os
import asyncio
from .get_token import get_token

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from concierge_backend_lib.document_collections import create_collection
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "-n",
    "--name",
    required=True,
    help="Name for new collection.",
)
parser.add_argument(
    "-o",
    "--owner",
    required=False,
    help="Username ownership of this collection should be assigned to. Only required if Concierge security is enabled.",
)
parser.add_argument(
    "-t",
    "--type",
    required=False,
    help="Collection type (private or shared). Only required if Concierge security is enabled.",
)
args = parser.parse_args()

collection_name = args.name
collection_owner = args.owner
collection_type = args.type

asyncio.run(
    create_collection(get_token()["access_token"], collection_name, collection_type)
)
