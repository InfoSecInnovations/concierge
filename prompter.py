import json
import random
import requests
# line below commented; future feature.
# import antigravity
from configparser import ConfigParser
from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer


### VARs ###
# % chance of a parting comment after a response
# must be 0-100. can be decimal if desired. no trailing %
enhancement_chance = 100
personafile = "personas/default.persona"
voicefile = "personas/voice.persona"
# will want to make this a select later
references = 5

### main program ###
### !!! this is not great... config with same keys start overwriting
# go to a single file? something else?
# could put all vars in a single config... then mount when we dockerize this
# kinda like that idea actually... 
config = ConfigParser()
config.read(personafile)
personas = config.sections()

config.read(voicefile)

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# DB connection info
conn = connections.connect(host="127.0.0.1", port=19530)
collection = Collection("facts")
collection.load()

search_params = {
    "metric_type": "IP"
}

while True:
    print("which persona do you want to work with?")
    print(personas)
    persona = input()
    greeting = config.get(persona, 'greeting')
    prompt = config.get(persona, 'prompt')

    enhancer = ""
    if enhancement_chance >= random.randrange(1, 100):
        enhancer_options = config.options('enhancer')
        enhancer_selection = (random.choice(enhancer_options))
        enhancer = config.get('enhancer', enhancer_selection)

    print(greeting)
    user_input = input()

    response = collection.search(
        data=[stransform.encode(user_input)],
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

    print('\nResponding based on the following sources:')
    for source in sources:
        if (source["type"] == "pdf"):
            metadata = json.loads(source["metadata"])
            print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]} located at {metadata["path"]}')

    if enhancer != "":
        prompt = prompt + "\n\n" + enhancer

    prompt = prompt + "\n\nContext: " + context + "\n\nUser input: " + user_input

    data={
        "model":"mistral",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post('http://127.0.0.1:11434/api/generate', data=json.dumps(data))

    result = json.loads(response.text)['response']
    print("\n\n")
    print(result)
    print("\n\n")
