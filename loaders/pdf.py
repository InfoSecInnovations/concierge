from langchain_community.document_loaders import PyPDFLoader

def LoadPDF(source_path, pdf):
    loader = PyPDFLoader(f'{source_path}{pdf}')
    pages = loader.load_and_split()
    return [{
        "metadata": str(f"Page {x.metadata['page']+1} of {pdf}"),
        "content": x.page_content
    } for x in pages]