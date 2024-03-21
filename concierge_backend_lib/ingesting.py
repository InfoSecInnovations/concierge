from pympler.asizeof import asizeof
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

chunk_size = 200
chunk_overlap = 25
max_batch_size = 60000000 # 67108864 is the true value but we're leaving a safety margin

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)

def insert (pages, collection):
    # on a huge dataset grpc can error due to size limits, so we need to break it into batches
    batched_entries = []
    batched_entries.append([])
    batch_index = 0
    batch_size = 0
    total = len(pages)
    for index, page in enumerate(pages):      
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
        yield (index, total)
    for batch in batched_entries:
        collection.insert([
            [x["metadata_type"] for x in batch],
            [x["metadata"] for x in batch],
            [x["text"] for x in batch],
            [x["vector"] for x in batch],
        ])

def insert_with_tqdm (pages, collection):
    page_progress = tqdm(total=len(pages))
    for x in insert(pages, collection):
        page_progress.n = x[0] + 1
        page_progress.refresh()
    page_progress.close()