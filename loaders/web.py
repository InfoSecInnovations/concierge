from langchain_community.document_loaders import PyPDFLoader
import json

def LoadWeb(url):
    loader = RecursiveUrlLoader(url, max_depth=100)
    pages = loader.load_and_split()
    return [{
        "metadata_type": "web",
        "metadata": json.dumps({'source': x.metadata['source'], 'title':  x.metadata['title'], 'language':  x.metadata['language']}),
        "content": x.page_content
    } for x in pages]
