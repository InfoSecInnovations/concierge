import json
import requests
# line below commented; future feature.
# import antigravity
from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer

def LoadModel():
    # TODO several revs in the future... allow users to pick model.
    # very much low priority atm
    models = requests.get("http://localhost:11434/api/tags")
    model_list = json.loads(models.text)['models']
    if not next(filter(lambda x: x['name'].split(':')[0] == 'mistral', model_list), None):
        print('mistral model not found. Please wait while it loads.')
        request = requests.post("http://localhost:11434/api/pull", data=json.dumps({"name": "mistral"}), stream=True)
        current = 0
        for item in request.iter_lines():
            if item:
                value = json.loads(item)
                # TODO: display statuses
                if 'total' in value:
                    if 'completed' in value:
                        current = value['completed']
                    yield (current, value['total'])

def InitCollection():
    # TODO make this into variable up top, or move to config file
    # will need to support non-local host better for very large deployments
    # DB connection info
    connections.connect(host="127.0.0.1", port=19530)
    # TODO make this be a selectable attribute
    collection = Collection("facts")
    collection.load()
    return collection

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')
search_params = {
    "metric_type": "IP"
}

def GetContext(collection, reference_limit, user_input):
    response = collection.search(
        data=[stransform.encode(user_input)],
        anns_field="vector",
        param=search_params,
        limit=reference_limit,
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
                "metadata": json.loads(hit.entity.get("metadata"))
            })

    return {
        "context": context,
        "sources": sources
    }

def PreparePrompt(context, task_prompt, user_input, persona_prompt = None, enhancer_prompts = None, source_file_contents = None):
    prompt = task_prompt

    if persona_prompt:
        prompt = persona_prompt + "\n\n" + prompt

    if enhancer_prompts:
        for enhancer_prompt in enhancer_prompts:
            prompt = prompt + "\n\n" + enhancer_prompt

    prompt = prompt + "\n\nContext: " + context + "\n\nUser input: " + user_input

    if source_file_contents:
        prompt = prompt + "\n\nSource file: " + source_file_contents

    return prompt

def GetResponse(context, task_prompt, user_input, persona_prompt = None, enhancer_prompts = None, source_file_contents = None):
    prompt = PreparePrompt(context, task_prompt, user_input, persona_prompt, enhancer_prompts, source_file_contents)

    data={
        "model":"mistral",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post('http://127.0.0.1:11434/api/generate', data=json.dumps(data))

    print(f"Response: {response}")

    return json.loads(response.text)['response']

def StreamResponse(context, task_prompt, user_input, persona_prompt = None, enhancer_prompts = None, source_file_contents = None):
    prompt = PreparePrompt(context, task_prompt, user_input, persona_prompt, enhancer_prompts, source_file_contents)

    data={
        "model":"mistral",
        "prompt": prompt,
        "stream": True
    }

    response = requests.post('http://127.0.0.1:11434/api/generate', data=json.dumps(data))

    for item in response.iter_lines():
        if item:
            value = json.loads(item)
            if 'response' in value:
                yield value ["response"]
