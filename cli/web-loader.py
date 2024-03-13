import platform
import sys

my_platform = platform.system()

if my_platform == "Linux": # relative imports don't work the same on Windows and Linux!
    sys.path.append('..')
# TODO: check MacOS

from loaders.web import load_web
from concierge_backend_lib.collections import init_collection
from concierge_backend_lib.ingesting import insert_with_tqdm
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--url", required=True, 
                    help="Required: the URL of the website you wish to scrape.")
parser.add_argument("-c", "--collection", required=True,
                    help="Milvus collection containing the vectorized data.")
args = parser.parse_args()
url = args.url

collection = init_collection(args.collection)

pages = load_web(url)
print (url)
if pages:
    insert_with_tqdm(pages, collection)

collection.flush() # if we don't flush, the Web UI won't be able to grab recent changes