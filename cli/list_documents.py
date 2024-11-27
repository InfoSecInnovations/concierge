import sys
import os
from .get_token import get_token

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from concierge_backend_lib.document_collections import get_documents
import asyncio

parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="Collection ID where the documents are stored.",
)
args = parser.parse_args()

collection_id = args.collection


async def display_documents():
    documents = await get_documents(get_token()["access_token"], collection_id)
    for document in documents:
        if "filename" in document:
            print(document["filename"])
        else:
            print(document["source"])
        print(
            f"id: {document['id']}, type: {document['type']}, pages: {document['page_count']}, vectors: {document['vector_count']}"
        )
        print("")


asyncio.run(display_documents())
