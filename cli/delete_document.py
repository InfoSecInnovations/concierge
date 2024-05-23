import sys
import os
# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from concierge_backend_lib.opensearch import get_client, delete_document

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--index", required=True,
                    help="OpenSearch index containing the vectorized data.")
parser.add_argument("-t", "--type", required=True,
                    help="Document type (use the documents command to list this value for existing documents)")
parser.add_argument("-s", "--source", required=True,
                    help="Document source (use the documents command to list this value for existing documents)")
args = parser.parse_args()

index_name = args.index
doc_type = args.type
doc_source = args.source

client = get_client()
print(f"{delete_document(client, index_name, doc_type, doc_source)} vectors deleted.")