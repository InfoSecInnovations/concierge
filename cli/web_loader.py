import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loaders.web import load_web
from concierge_backend_lib.opensearch import get_client, ensure_index, insert_with_tqdm
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "-u",
    "--url",
    required=True,
    help="Required: the URL of the website you wish to scrape.",
)
parser.add_argument(
    "-i",
    "--index",
    required=True,
    help="OpenSearch index containing the vectorized data.",
)
args = parser.parse_args()
url = args.url
index_name = args.index

client = get_client()
ensure_index(client, index_name)

pages = load_web(url)
print(url)
if pages:
    insert_with_tqdm(client, index_name, pages)
