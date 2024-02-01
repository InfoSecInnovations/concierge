# TODO: delete this script and use a persona in prompter.py

import weaviate
import json
import requests

from sentence_transformers import SentenceTransformer

references = 5
stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')


client = weaviate.Client(
    url = "http://127.0.0.1:8080"
)



#question = "is emacs better than vim?"

while True:
    print("what statement do you want to fact check?")
    question = input()

    response = (
        client.query
        .get("Fact", ["metadata", "text"])
        .with_near_vector({
            "vector": stransform.encode(question)
        })
        .with_limit(references)
        .with_additional(["distance"])
        .do()
    )


    context = ""
    sources = []
    for resp in response['data']['Get']['Fact']:
        context = context + resp['text']
        sources.append(resp['metadata'])


#    print('Will be answering from:')
#    for source in sources:
#        print(f'   {source}')

    data={
        "model":"mistral",
        "prompt":f"Using only the context provided, determine if the statement that follows is true or not. "\
                 f"\n\nContext: {context}\n\nstatement:{question}. "\
                 f"You must evaluate the truth of the statement with only the provided context",
        "stream": False
    }


    response = requests.post('http://127.0.0.1:11434/api/generate', data=json.dumps(data))

    result = json.loads(response.text)['response']
    #result = json.loads(response.text)
    print(result)
    #for i in range(len(result)//80):
    #    print(result[i*80:(i+1)*80])
    print("------")
    print('For more information see:')
    for source in sources:
        print(f'   {source}')
    print("\n\n")
