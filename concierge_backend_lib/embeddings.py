from sentence_transformers import SentenceTransformer

stransform = SentenceTransformer("paraphrase-MiniLM-L6-v2")


def create_embeddings(text):
    return stransform.encode(text)
