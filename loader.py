from dotenv import load_dotenv
import os
from loaders.pdf import LoadPDF
from concierge_backend_lib.collections import InitCollection
from concierge_backend_lib.ingesting import InsertWithTqdm

load_dotenv()

# variables
source_path = os.environ['DOCS_DIR']

source_files = os.listdir(source_path)
collection = InitCollection("facts")

for file in source_files:
    print(file)
    pages = None
    if (file.endswith(".pdf")):
        pages = LoadPDF(source_path, file)
    if (pages):
        InsertWithTqdm(pages, collection)