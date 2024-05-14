import sys
import os
# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from concierge_backend_lib.opensearch import get_client

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--index", required=True,
                    help="OpenSearch index containing the vectorized data.")
args = parser.parse_args()

index_name = args.index
client = get_client()
response = client.indices.delete(
    index = index_name
)

print(response)