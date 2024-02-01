#import weaviate
import json
import requests
from pymilvus import connections, Collection

from sentence_transformers import SentenceTransformer

references = 5
stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')


""" client = weaviate.Client(
    url = "http://127.0.0.1:8080"
) """

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
        output_fields=["metadata", "text"],
        expr=None,
        consistency_level="Strong"
    )
    """     response = (
        client.query
        .get("Fact", ["metadata", "text"])
        .with_near_vector({
            "vector": stransform.encode(question)
        })
        .with_limit(references)
        .with_additional(["distance"])
        .do()
    ) """
    context = ""
    sources = []
    for resp in response:
        for hit in resp:
            context = context + hit.entity.get("text")
            sources.append(hit.entity.get("metadata"))
    """ for resp in response['data']['Get']['Fact']:
        context = context + resp['text']
        sources.append(resp['metadata']) """


    print('Will be answering from:')
    for source in sources:
        print(f'   {source}')

    data={
        "model":"mistral",
        "prompt":f"Using only the context provided answer the question that follows. "\
                 f"Context: {context}\n\nQuestion:{question}. "\
                 f"You must limit the response to the provided context",
        "stream": False
    }


    response = requests.post('http://127.0.0.1:11434/api/generate', data=json.dumps(data))

    result = json.loads(response.text)['response']
    #result = json.loads(response.text)
    print(result)
    #for i in range(len(result)//80):
    #    print(result[i*80:(i+1)*80])
    #print("------")
    #print('For more information see:')
    #for source in sources:
    #    print(f'   {source}')
    print("\n\n")
