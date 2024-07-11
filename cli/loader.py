import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import shutil
from concierge_backend_lib.opensearch import get_client, ensure_collection
from concierge_backend_lib.ingesting import insert_with_tqdm
from concierge_backend_lib.loading import load_file

upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))

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
    uploaded_path = os.path.join(upload_dir, file)
    shutil.copyfile(os.path.join(source_path, file), uploaded_path)
    print(file)
    doc = load_file(upload_dir, file)
    if doc:
        insert_with_tqdm(client, collection, doc)
