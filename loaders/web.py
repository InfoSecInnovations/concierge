from bs4 import BeautifulSoup
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from datetime import datetime
import json


date_time = datetime.now()
str_date_time = date_time.isoformat()


def LoadWeb(url):
    loader = RecursiveUrlLoader(url, max_depth=100)
    pages = loader.load_and_split()
    return [{
        "metadata_type": "web",
        "metadata": json.dumps({'source': x.metadata['source'], \
                                'title':  x.metadata['title'], \
                                'language':  x.metadata['language'], \
                                'ingest_date': str_date_time}),
        "content": x.page_content
    } for x in pages]
