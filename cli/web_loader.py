import sys
import os
from .get_token import get_token

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loaders.web import WebLoader
from concierge_backend_lib.ingesting import insert_with_tqdm
import argparse
import asyncio

parser = argparse.ArgumentParser()
parser.add_argument(
    "-u",
    "--url",
    required=True,
    help="The URL of the website you wish to scrape.",
)
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="Collection ID of document collection to load into.",
)
args = parser.parse_args()
url = args.url
collection_id = args.collection

pages = WebLoader.load(url)
print(url)
if pages:
    asyncio.run(insert_with_tqdm(get_token()["access_token"], collection_id, pages))
