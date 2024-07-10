import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from concierge_backend_lib.opensearch import get_client, delete_collection

parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="Collection containing the vectorized data.",
)
args = parser.parse_args()

collection_name = args.collection

client = get_client()
print(delete_collection(client, collection_name))
