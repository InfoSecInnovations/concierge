from langchain_community.document_loaders import TextLoader
import time
import os

date_time = int(round(time.time() * 1000))


def load_text(source_path, filename):
    source = os.path.join(source_path, filename)
    loader = TextLoader(source)
    docs = loader.load()
    return [
        {
            "metadata_type": "plaintext",
            "metadata": {
                "source": source,
                "filename": filename,
                "ingest_date": date_time,
                "extension": os.path.splitext(source)[1],
            },
            "content": doc.page_content,
        }
        for doc in docs
    ]
