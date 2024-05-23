import sys
import os
# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from concierge_backend_lib.opensearch import get_client, get_documents

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--index", required=True,
                    help="OpenSearch index containing the vectorized data.")
args = parser.parse_args()

index_name = args.index

client = get_client()
documents = get_documents(client, index_name)

for document in documents:
    print(f"source: {document['source']}, type: {document['type']}, vectors: {document['vector_count']})")

