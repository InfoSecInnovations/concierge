from dotenv import load_dotenv
import os
from loaders.pdf import LoadPDF
from loader_functions import Insert, InitCollection

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
        Insert(pages, collection)