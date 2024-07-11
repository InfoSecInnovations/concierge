import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loaders.web import WebLoader
from concierge_backend_lib.opensearch import get_client, ensure_collection
from concierge_backend_lib.ingesting import insert_with_tqdm
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "-u",
    "--url",
    required=True,
    help="Required: the URL of the website you wish to scrape.",
)
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="Collection containing the vectorized data.",
)
args = parser.parse_args()
url = args.url
collection_name = args.collection

client = get_client()
ensure_collection(client, collection_name)

pages = WebLoader.load(url)
print(url)
if pages:
    insert_with_tqdm(client, collection_name, pages)
