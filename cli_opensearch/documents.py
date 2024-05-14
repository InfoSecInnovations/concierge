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

query = {
  "size": 0,
  "aggs": {
    "documents": {
        "multi_terms": {
            "size": 10000,
            "terms": [
                {
                    "field": "metadata_type"
                },
                {
                    "field": "metadata.source",
                } 

            ]
        }
    }
  }
}

client = get_client()

response = client.search(
    body = query,
    index = index_name
)

for bucket in response["aggregations"]["documents"]["buckets"]:
    print(bucket["key"])
    print(f"chunks: {bucket['doc_count']}")

