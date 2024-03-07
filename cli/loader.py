import os
from loaders.pdf import LoadPDF
from concierge_backend_lib.collections import InitCollection
from concierge_backend_lib.ingesting import InsertWithTqdm
import argparse
import shutil

upload_dir = os.path.join('..', 'uploads')

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
    shutil.copyfile(os.path.join(source_path, file), os.path.join(upload_dir, file))
    print(file)
    pages = None
    if file.endswith(".pdf"):
        pages = LoadPDF(upload_dir, file)
    if pages:
        InsertWithTqdm(pages, collection)

collection.flush() # if we don't flush, the Web UI won't be able to grab recent changes