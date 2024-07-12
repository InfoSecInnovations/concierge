import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from concierge_backend_lib.opensearch import get_client, delete_document

parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="collection containing the document.",
)
parser.add_argument(
    "-t",
    "--type",
    required=True,
    help="type of document",
)
parser.add_argument(
    "-i",
    "--id",
    required=True,
    help="ID of document",
)
args = parser.parse_args()

collection_name = args.collection
doc_type = args.type
doc_id = args.id

client = get_client()
print(f"{delete_document(client, collection_name, doc_type, doc_id)} entities deleted.")
