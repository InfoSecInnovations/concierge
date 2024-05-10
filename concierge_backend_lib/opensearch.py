import os
from dotenv import load_dotenv
from opensearchpy import OpenSearch, helpers
from pympler.asizeof import asizeof
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

load_dotenv()
OPENSEARCH_INITIAL_ADMIN_PASSWORD = os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD")

chunk_size = 200
chunk_overlap = 25
max_batch_size = 60000000 # 67108864 is the true value but we're leaving a safety margin

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)

def get_client():
    host = 'localhost'
    port = 9200
    auth = ('admin', OPENSEARCH_INITIAL_ADMIN_PASSWORD)

    return OpenSearch(
        hosts = [{'host': host, 'port': port}],
        http_auth = auth,
        use_ssl=True,
        verify_certs = False,
        ssl_show_warn=False
    )

def ensure_index(client, index_name):
    index_body = {
        "settings": {
            "index": {
                "knn": True
            }
        },
        "mappings": {
            "properties": {
                "vector": {
                    "type": "knn_vector",
                    "dimension": 384,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib",
                        "parameters": {}
                    }
                }
            }
        }
    }

    if not client.indices.exists(index_name):
        client.indices.create(
            index_name, 
            body=index_body
        )

def insert (client, index_name, pages):
    entries = []
    total = len(pages)
    for index, page in enumerate(pages):      
        chunks = splitter.split_text(page["content"])
        for chunk in chunks:
            vect = stransform.encode(chunk)
            entry = {
                "_index": index_name,
                "metadata_type":page["metadata_type"],
                "metadata":page["metadata"],
                "text":chunk,
                "vector":vect
            }
            entries.append(entry)
        yield (index, total)
    helpers.bulk(client, entries)

def insert_with_tqdm (client, index_name, pages):
    page_progress = tqdm(total=len(pages))
    for x in insert(client, index_name, pages):
        page_progress.n = x[0] + 1
        page_progress.refresh()
    page_progress.close()