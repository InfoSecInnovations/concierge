import sys
import os
from .get_token import get_token

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import asyncio
from concierge_backend_lib.ingesting import insert_with_tqdm
from concierge_backend_lib.loading import load_file


parser = argparse.ArgumentParser()
parser.add_argument(
    "-s",
    "--source",
    required=True,
    help="Path of the directory containing the files to ingest.",
)
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="Collection ID of document collection to load into.",
)
args = parser.parse_args()
source_path = args.source
collection_id = args.collection

source_files = os.listdir(source_path)


async def load_files():
    for file in source_files:
        print(file)
        full_path = os.path.join(source_path, file)
        with open(full_path, "rb") as f:
            binary = f.read()
        doc = load_file(full_path)
        if doc:
            # we should just get token each iteration to avoid refresh issues
            doc_id = await insert_with_tqdm(
                get_token()["access_token"], collection_id, doc, binary
            )
            print(f"inserted with document ID {doc_id}")


asyncio.run(load_files())
