from tqdm import tqdm
from pympler.asizeof import asizeof
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection

chunk_size = 200
chunk_overlap = 25
max_batch_size = 60000000 # 67108864 is the true value but we're leaving a safety margin

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)

def Insert (pages, collection):
    # on a huge dataset grpc can error due to size limits, so we need to break it into batches
    batched_entries = []
    batched_entries.append([])
    batch_index = 0
    batch_size = 0 
    page_progress = tqdm(total=len(pages))
    for page in pages:
        page_progress.update(1)
        chunks = splitter.split_text(page["content"])
        for chunk in chunks:
            vect = stransform.encode(chunk)
            entry = {
                "metadata_type":page["metadata_type"],
                "metadata":page["metadata"],
                "text":chunk,
                "vector":vect
            }
            entry_size = asizeof(entry)
            if (batch_size + entry_size > max_batch_size):
                batched_entries.append([])
                batch_index = batch_index + 1
                batch_size = 0
            batched_entries[batch_index].append(entry)
            batch_size = batch_size + entry_size
    for batch in batched_entries:
        collection.insert([
            [x["metadata_type"] for x in batch],
            [x["metadata"] for x in batch],
            [x["text"] for x in batch],
            [x["vector"] for x in batch],
        ])

def InitCollection (collection_name):
    connections.connect(host="127.0.0.1", port=19530)
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="metadata_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384)
    ]
    schema = CollectionSchema(fields=fields, description=collection_name)
    collection = Collection(name=collection_name, schema=schema)
    index_params={
        "metric_type":"IP",
        "index_type":"IVF_FLAT",
        "params":{"nlist":128}
    }
    collection.create_index(field_name="vector", index_params=index_params)
    return collection