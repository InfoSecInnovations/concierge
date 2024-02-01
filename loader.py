from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from dotenv import load_dotenv
import os
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
# import weaviate

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

""" client = weaviate.Client(
    url = "http://127.0.0.1:8080"
) """

conn = connections.connect(host="127.0.0.1", port=19530)

class_obj = {
    "class": "Fact",
    "properties": [
        {
            "name": "metadata",
            "dataType": ["text"],
        },
        {
            "name": "text",
            "dataType": ["text"],
        },
    ],
}

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384)
]
schema = CollectionSchema(fields=fields, description="Vectorized PDFs")
collection = Collection(name="facts", schema=schema)
index_params={
    "metric_type":"IP",
    "index_type":"IVF_FLAT",
    "params":{"nlist":128}
}
collection.create_index(field_name="vector", index_params=index_params)
entries = []

def VectorizePDF(pdf):
    loader = PyPDFLoader(f'{source_path}{pdf}')
    pages = loader.load_and_split()
    PageProgress = tqdm(total=len(pages))
    for page in pages:
        PageProgress.update(1)
        metadata = page.metadata
        chunks = splitter.split_text(page.page_content)
        for chunk in chunks:
            vect = stransform.encode(chunk)
            entries.append({
                "metadata":str(f"Page {metadata['page']+1} of {pdf}"),
                "text":chunk,
                "vector":vect
            })
"""             client.data_object.create(class_name="Fact",
                                      data_object={
                                          "metadata":str(f"Page {metadata['page']+1} of {pdf}"),
                                          "text":chunk,
                                          },
                                          vector = vect
            ) """
    


# client.schema.create_class(class_obj) 

for pdf in source_files:
    print(pdf)
    VectorizePDF(pdf)

collection.insert([
    [x["metadata"] for x in entries],
    [x["text"] for x in entries],
    [x["vector"] for x in entries],
])
