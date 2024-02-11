from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from loaders.pdf import LoadPDF
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
from pympler.asizeof import asizeof
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import os

# multithreading experiement
#import threading
#import psutil

# multiprocessing experiment
import multiprocessing


load_dotenv()

# variables
source_path = os.environ['DOCS_DIR']
source_files = os.listdir(source_path)
chunk_size = 200
chunk_overlap = 25
stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')


splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)

conn = connections.connect(host="127.0.0.1", port=19530)

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="metadata_type", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384)
]
schema = CollectionSchema(fields=fields, description="vectorized facts")
collection = Collection(name="facts", schema=schema)
index_params={
    "metric_type":"IP",
    "index_type":"IVF_FLAT",
    "params":{"nlist":128}
}
collection.create_index(field_name="vector", index_params=index_params)

# on a huge dataset grpc can error due to size limits, so we need to break it into batches
#batched_entries = []
#batched_entries.append([])
#batch_index = 0
#batch_size = 0
#max_batch_size = 60000000 # 67108864 is the true value but we're leaving a safety margin

#def Vectorize(pages):
#    #global batch_index
#    #global batch_size
#    #PageProgress = tqdm(total=len(pages))
#    for page in pages:
#        #PageProgress.update(1)
#        chunks = splitter.split_text(page["content"])
#        for chunk in chunks:
#            vect = stransform.encode(chunk)
#            entry = {
#                "metadata_type":page["metadata_type"],
#                "metadata":page["metadata"],
#                "text":chunk,
#                "vector":vect
#            }
#            #entry_size = asizeof(entry)
#            #if (batch_size + entry_size > max_batch_size):
#            #    batched_entries.append([])
#            #    batch_index = batch_index + 1
#            #    batch_size = 0
#            #batched_entries[batch_index].append(entry)
#            #batch_size = batch_size + entry_size
#        #insert each page's vectors
#        collection.insert([
#            [x["metadata"] for x in entries],
#            [x["text"] for x in entries],
#            [x["vector"] for x in entries],
#        ])

def chunker(pages):
    for page in pages:
        chunks = slitter.split_text(page["content"])

def vect_chunk(chunks):
    for chunk in chunks:
        vect = stransform.encode(chunk)
        entry = {
            "metadata_type":page["metadata_type"],
            "metadata":page["metadata"],
            "text":chunk,
            "vector":vect
        }
        collection.insert(entry)

##def inserter(entry):
#        collection.insert([
#            [entry["metadata"]],
#            [entry["text"]],
#            [entry["vector"]],
#        ])


def load_check():
    load1, load5, load15 = psutil.getloadavg()
    cpu_usage = (load5/os.cpu_count()) * 100
    if (cpu_usage <= 80):
        return True
    else:
        return False


for file in source_files:
    print(file)
    pages = None

    #load1, load5, load15 = psutil.getloadavg()
    #cpu_usage = (load5/os.cpu_count()) * 100

    if (file.endswith(".pdf")):
        pages = LoadPDF(source_path, file)
    if (pages):
        # original method: serial processing
        #Vectorize(pages)

        # multithreading experiment
        #chunks = threading.Thread(target=chunker, args=pages).start
        #entry = threading.Thread(target=vect_chunk, args=chunks).start
        #inserter(entry)

        # multiprocessing experiment
        chunks = multiprocessing.Process(target=chunker, args=pages).start
        entry = multiprocessing.Process(target=vect_chunk, args=chunks).start

# MBD: I love batching, but would need to refactor for multithread/multiprocess support
#for batch in batched_entries:
#    collection.insert([
#        [x["metadata_type"] for x in batch],
#        [x["metadata"] for x in batch],
#        [x["text"] for x in batch],
#        [x["vector"] for x in batch],
#    ])
