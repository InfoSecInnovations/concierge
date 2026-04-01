import torch
import onnxruntime
from sentence_transformers import SentenceTransformer

# from fastembed import TextEmbedding
import os
from src.app.ollama import do_loading
import requests
import json
import time
from langchain_text_splitters import SentenceTransformersTokenTextSplitter


print(os.getenv("SHABTI_COMPUTE"))

print("torch cuda is available: " + "Yes" if torch.cuda.is_available() else "No")

print("torch cuda version " + torch.version.cuda)
print("torch cudnn version: " + str(torch.backends.cudnn.version()))

print("preload DLLs")
onnxruntime.preload_dlls()
print(onnxruntime.get_available_providers())

stransform = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)

# model = TextEmbedding(
#     model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
#     cache_dir=os.getenv("SHABTI_MODELS_DIR"),
#     providers=["CUDAExecutionProvider"]
# )

for _ in do_loading("paraphrase-multilingual"):
    pass

splitter = SentenceTransformersTokenTextSplitter(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)

host = os.getenv("OLLAMA_HOST", "localhost")


def create_embeddings_ollama(text):
    data = {"model": "paraphrase-multilingual", "input": text, "stream": False}
    response = requests.post(
        f"http://{host}:11434/api/embed", data=json.dumps(data)
    ).json()
    return response["embeddings"]


with open("bench_text.txt") as f:
    text = f.read()
split = splitter.split_text(text)
print(len(split))

print("start embeddings bench")

# # FastEmbed
# start = time.perf_counter()
# embeddings = list(model.embed(split))
# end = time.perf_counter()
# print(len(embeddings))
# print(embeddings[0][0])
# print(f"FastEmbed took {end - start}s")

# Sentence Transformers
start = time.perf_counter()
embeddings = stransform.encode(split)
end = time.perf_counter()
print(len(embeddings))
print(embeddings[0][0])
print(f"Sentence Transformers took {end - start}s")

# Ollama
start = time.perf_counter()
embeddings = create_embeddings_ollama(split)
end = time.perf_counter()
print(len(embeddings))
print(embeddings[0][0])
print(f"Ollama took {end - start}s")

print("end embedding bench")
