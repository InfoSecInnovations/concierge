from loaders.web import LoadWeb
from loader_functions import Insert, InitCollection
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('url')
args = parser.parse_args()
url = args.url

collection = InitCollection("facts")

pages = LoadWeb(url)
print (url)
if (pages):
    Insert(pages, collection)