from shabti_api_client import ShabtiClient
from importlib.resources import files
import os
import time
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import SentenceTransformersTokenTextSplitter
from sentence_transformers import SentenceTransformer

splitter = SentenceTransformersTokenTextSplitter(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)

stransform = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)


async def bench_api():
    print("Benchmark Shabti API document ingest calls")
    client = ShabtiClient("http://localhost:8000")
    collection_id = await client.create_collection("bench_collection")
    doc_dir = os.path.join(files(), "docs")
    source_files = os.listdir(doc_dir)
    file_paths = [os.path.join(doc_dir, file) for file in source_files]
    print(file_paths)
    start = time.perf_counter()
    async for _ in client.insert_files(collection_id, file_paths):
        pass
    end = time.perf_counter()
    print(f"Operation took {end - start}s")
    await client.delete_collection(collection_id)
    print("")


def bench_splitting():
    print("Benchmark text splitter")
    doc_dir = os.path.join(files(), "docs")
    source_files = os.listdir(doc_dir)
    file_paths = [os.path.join(doc_dir, file) for file in source_files]
    print(file_paths)
    start = time.perf_counter()
    count = 0
    for full_path in file_paths:
        loader = TextLoader(full_path, autodetect_encoding=True)
        pages = loader.load()
        for page in pages:
            chunks = splitter.split_text(page.page_content)
            count += len(chunks)
    end = time.perf_counter()
    print(f"Operation took {end - start}s")
    print(f"{count} chunks")
    print("")


def bench_embedding():
    print("Benchmark embeddings")
    doc_dir = os.path.join(files(), "docs")
    source_files = os.listdir(doc_dir)
    file_paths = [os.path.join(doc_dir, file) for file in source_files]
    print(file_paths)
    chunks = []

    for full_path in file_paths:
        loader = TextLoader(full_path, autodetect_encoding=True)
        pages = loader.load()
        for page in pages:
            chunks.extend(splitter.split_text(page.page_content))
    print(f"{len(chunks)} chunks")
    start = time.perf_counter()
    stransform.encode(chunks)
    end = time.perf_counter()
    print(f"Operation took {end - start}s")
    print("")


if __name__ == "__main__":
    # asyncio.run(bench_api())
    bench_splitting()
    bench_embedding()
