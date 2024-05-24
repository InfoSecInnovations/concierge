from langchain_community.document_loaders import PyPDFLoader
import os
import time

date_time = int(round(time.time() * 1000))


def load_pdf(source_path, pdf):
    source = os.path.join(source_path, pdf)
    loader = PyPDFLoader(source)
    pages = loader.load_and_split()
    return [
        {
            "metadata_type": "pdf",
            "metadata": {
                "page": x.metadata["page"] + 1,
                "source": source,
                "filename": pdf,
                "ingest_date": date_time,
            },
            "content": x.page_content,
        }
        for x in pages
    ]
