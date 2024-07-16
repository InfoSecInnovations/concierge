import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from concierge_backend_lib.opensearch import get_client, ensure_collection
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
    help="Collection containing the vectorized data.",
)
args = parser.parse_args()
source_path = args.source
collection = args.collection

source_files = os.listdir(source_path)

client = get_client()
ensure_collection(client, collection)

for file in source_files:
    print(file)
    full_path = os.path.join(source_path, file)
    with open(full_path, "rb") as f:
        binary = f.read()
    doc = load_file(full_path)
    if doc:
        insert_with_tqdm(client, collection, doc, binary)
