from sentence_transformers import SentenceTransformer
import json
import requests
import time

start = time.time()
stransform = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
end = time.time()
print(f"Sentence transformer model init took {end - start}s")


def create_st_embeddings(text):
    return stransform.encode(text)


def create_embeddings_ollama(text):
    data = {"model": "paraphrase-multilingual", "input": text, "stream": False}
    response = requests.post(
        "http://localhost:11434/api/embed", data=json.dumps(data)
    ).json()
    return response["embeddings"]


def create_embeddings_localai(text):
    data = {"model": "paraphrase-multilingual", "input": text}
    response = requests.post(
        "http://localhost:11435/v1/embeddings",
        data=json.dumps(data),
        headers={"accept": "application/json", "Content-type": "application/json"},
    ).json()
    return response["data"]


def test_speed():
    inputs = [
        "Lorem ipsum",
        "dolor sit amet,",
        "consectetur adipiscing elit,",
        "sed do",
        "eiusmod tempor incididunt ut labore et dolore magna aliqua",
    ]
    start = time.time()
    for i in range(100):
        create_st_embeddings(inputs)
    end = time.time()
    print(f"Sentence transformer took {end - start}s")
    start = time.time()
    for i in range(100):
        create_embeddings_ollama(inputs)
    end = time.time()
    print(f"Ollama took {end - start}s")
    start = time.time()
    for i in range(100):
        create_embeddings_localai(inputs)
    end = time.time()
    print(f"LocalAI took {end - start}s")


if __name__ == "__main__":
    test_speed()
