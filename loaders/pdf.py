from langchain_community.document_loaders import PyPDFLoader
import json

def LoadPDF(source_path, pdf):
    loader = PyPDFLoader(f'{source_path}{pdf}')
    pages = loader.load_and_split()
    return [{
        "metadata_type": "pdf",
        "metadata": json.dumps({"page": x.metadata['page']+1, "path": source_path, "filename": pdf}),
        "content": x.page_content
    } for x in pages]