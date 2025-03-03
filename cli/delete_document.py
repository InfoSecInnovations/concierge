import sys
import os
from get_token import get_token

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import asyncio
from concierge_backend_lib.document_collections import delete_document
from concierge_scripts.load_dotenv import load_env

load_env()

parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="Collection ID containing the document.",
)
parser.add_argument(
    "-t",
    "--type",
    required=True,
    help="type of document",
)
parser.add_argument(
    "-d",
    "--doc",
    required=True,
    help="ID of document",
)
args = parser.parse_args()

collection_id = args.collection
doc_type = args.type
doc_id = args.doc

asyncio.run(
    delete_document(get_token()["access_token"], collection_id, doc_type, doc_id)
)
print(
    f"Deleted document with ID {doc_id} of type {doc_type} from collection with ID {collection_id}"
)
