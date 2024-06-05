import sys
import os
from binaryornot.check import is_binary

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loaders.pdf import load_pdf
from loaders.text import load_text
import argparse
import shutil
from concierge_backend_lib.opensearch import get_client, ensure_index, insert_with_tqdm

upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))

parser = argparse.ArgumentParser()
parser.add_argument(
    "-s",
    "--source",
    required=True,
    help="Path of the directory containing the files to ingest.",
)
parser.add_argument(
    "-i",
    "--index",
    required=True,
    help="OpenSearch index containing the vectorized data.",
)
args = parser.parse_args()
source_path = args.source
index = args.index

source_files = os.listdir(source_path)

client = get_client()
ensure_index(client, index)

for file in source_files:
    uploaded_path = os.path.join(upload_dir, file)
    shutil.copyfile(os.path.join(source_path, file), uploaded_path)
    print(file)
    pages = None
    if file.endswith(".pdf"):
        pages = load_pdf(upload_dir, file)
    elif not is_binary(uploaded_path):
        try:  # generic text loader doesn't always succeed so we should catch the exception
            pages = load_text(upload_dir, file)
        except Exception:
            print(f"{uploaded_path} was unable to be ingested as plaintext")
            pages = None
    if pages:
        insert_with_tqdm(client, index, pages)
