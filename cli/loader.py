import os
from loaders.pdf import LoadPDF
from concierge_backend_lib.collections import InitCollection
from concierge_backend_lib.ingesting import InsertWithTqdm
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--source", required=True, 
                    help="Path of the directory containing the files to ingest.")
parser.add_argument("-c", "--collection", required=True,
                    help="Milvus collection containing the vectorized data.")
args = parser.parse_args()
source_path = args.source

source_files = os.listdir(source_path)
collection = InitCollection(args.collection)

for file in source_files:
    print(file)
    pages = None
    if file.endswith(".pdf"):
        pages = LoadPDF(source_path, file)
    if pages:
        InsertWithTqdm(pages, collection)