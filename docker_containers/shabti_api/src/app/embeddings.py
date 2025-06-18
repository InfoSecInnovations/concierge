from sentence_transformers import SentenceTransformer

print(
    "initializing embeddings model (if this is the first run, it can take some time)..."
)

stransform = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)


def create_embeddings(text):
    return stransform.encode(text)


# from .ollama import create_embeddings_ollama

# def create_embeddings(text):
#     return create_embeddings_ollama(text)
