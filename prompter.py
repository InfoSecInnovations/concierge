import json
import random
import requests
# line below commented; future feature.
# import antigravity
from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer
import argparse
from configobj import ConfigObj

parser = argparse.ArgumentParser()
parser.add_argument("--task", required=True)
parser.add_argument("--persona")
parser.add_argument("--enhancers", nargs="*")
args = parser.parse_args()

enhancer_options = None
if args.enhancers:
    enhancer_options = [ConfigObj(f"prompter_config/enhancers/{enhancer}.concierge", list_values=False) for enhancer in args.enhancers]

persona = None
if args.persona:
    persona = ConfigObj(f"prompter_config/personas/{args.persona}.concierge", list_values=False)

task = ConfigObj(f"prompter_config/tasks/{args.task}.concierge", list_values=False)

### VARs ###
# % chance of a parting comment after a response
# must be 0-100. can be decimal if desired. no trailing %
enhancement_chance = 100
# will want to make this a select later
references = 5

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# DB connection info
conn = connections.connect(host="127.0.0.1", port=19530)
collection = Collection("facts")
collection.load()

search_params = {
    "metric_type": "IP"
}

while True:

    enhancer = None
    if enhancer_options and len(enhancer_options) and enhancement_chance >= random.randrange(1, 100):
        enhancer_selection = (random.choice(enhancer_options))
        enhancer = enhancer_selection['prompt']

    print(task['greeting'])
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
        if source["type"] == "pdf":
            metadata = json.loads(source["metadata"])
            print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]} located at {metadata["path"]}')

    prompt = task['prompt']
    if enhancer:
        prompt = prompt + "\n\n" + enhancer
    if persona:
        prompt = persona['prompt'] + "\n\n" + prompt
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
