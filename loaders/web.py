from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
import time

date_time = int(round(time.time() * 1000))


def load_web(url):
    loader = RecursiveUrlLoader(url, max_depth=100)
    pages = loader.load_and_split()
    return [
        {
            "metadata_type": "web",
            "metadata": {
                "source": x.metadata["source"],
                "title": None if "title" not in x.metadata else x.metadata["title"],
                "language": None
                if "language" not in x.metadata
                else x.metadata["language"],
                "ingest_date": date_time,
            },
            "content": x.page_content,
        }
        for x in pages
    ]
