from loaders.web import LoadWeb
from concierge_backend_lib.collections import InitCollection
from concierge_backend_lib.ingesting import InsertWithTqdm
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('url', required=True, help="Required: the URL of the website you wish to scrape.")
args = parser.parse_args()
url = args.url

collection = InitCollection("facts")

pages = LoadWeb(url)
print (url)
if pages:
    InsertWithTqdm(pages, collection)

collection.flush() # if we don't flush, the Web UI won't be able to grab recent changes