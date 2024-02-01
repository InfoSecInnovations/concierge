from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from dotenv import load_dotenv
import os
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
from loaders.pdf import LoadPDF

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

entries = []
def Vectorize(pages):
    PageProgress = tqdm(total=len(pages))
    for page in pages:
        PageProgress.update(1)
        chunks = splitter.split_text(page["content"])
        for chunk in chunks:
            vect = stransform.encode(chunk)
            entries.append({
                "metadata_type":page["metadata_type"],
                "metadata":page["metadata"],
                "text":chunk,
                "vector":vect
            })

for file in source_files:
    print(file)
    pages = None
    if (file.endswith(".pdf")):
        pages = LoadPDF(source_path, file)
    if (pages):
        Vectorize(pages)

collection.insert([
    [x["metadata_type"] for x in entries],
    [x["metadata"] for x in entries],
    [x["text"] for x in entries],
    [x["vector"] for x in entries],
])
