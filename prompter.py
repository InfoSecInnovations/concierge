import json
import requests
from pymilvus import connections, Collection

from sentence_transformers import SentenceTransformer

references = 5
stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

conn = connections.connect(host="127.0.0.1", port=19530)
collection = Collection("facts")
collection.load()

search_params = {
    "metric_type": "IP"
}

while True:
    print("what do you want to know?")
    question = input()
    response = collection.search(
        data=[stransform.encode(question)],
        anns_field="vector",
        param=search_params,
        limit=references,
        output_fields=["metadata_type", "metadata", "text"],
        expr=None,
        consistency_level="Strong"
    )

    context = ""
    sources = []
    for resp in response:
        for hit in resp:
            context = context + hit.entity.get("text")
            sources.append({
                "type": hit.entity.get("metadata_type"),
                "metadata": hit.entity.get("metadata")
            })

    print('Will be answering from:')
    for source in sources:
        if (source["type"] == "pdf"):
            metadata = json.loads(source["metadata"])
            print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]} located at {metadata["path"]}')

    data={
        "model":"mistral",
        "prompt":f"Using only the context provided answer the question that follows. "\
                 f"Context: {context}\n\nQuestion:{question}. "\
                 f"You must limit the response to the provided context",
        "stream": False
    }

    response = requests.post('http://127.0.0.1:11434/api/generate', data=json.dumps(data))

    result = json.loads(response.text)['response']
    print(result)
    print("\n\n")