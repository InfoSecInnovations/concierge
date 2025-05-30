from sentence_transformers import SentenceTransformer

# This script triggers the model download so we can roll it into the Docker image

SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
