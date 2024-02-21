from loaders.web import LoadWeb
from loader_functions import InsertWithTqdm, InitCollection
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('url', required=True, help="Required: the URL of the website you wish to scrape.")
args = parser.parse_args()
url = args.url

collection = InitCollection("facts")

pages = LoadWeb(url)
print (url)
if (pages):
    InsertWithTqdm(pages, collection)