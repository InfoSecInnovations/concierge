from langchain_community.document_loaders import Docx2txtLoader
import os
import time

# Get the current timestamp in milliseconds
date_time = int(round(time.time() * 1000))

def load_docx(source_path, docx_filename):
    
    source = os.path.join(source_path, docx_filename)
    
    loader = Docx2txtLoader(source)

    pages = loader.load_and_split()
    
    return [
        {
            "metadata_type": "docx",
            "metadata": {
                "page": x.metadata.get("page", 0) + 1,
                "source": source,
                "filename": docx_filename,
                "ingest_date": date_time,
            },
            "content": x.page_content,
        }
        for x in pages
    ]