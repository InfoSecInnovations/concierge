import json
import os
import requests
# line below commented; future feature.
# import antigravity
from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer
from configobj import ConfigObj
from tqdm import tqdm

# TODO add collection as an option
# TODO make these be web inputs for streamlit



### VARs ###
# TODO will want to make this a select later
references = 5


stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# TODO make this into variable up top, or move to config file
# will need to support non-local host better for very large deployments
# DB connection info
conn = connections.connect(host="127.0.0.1", port=19530)
# TODO make this be a selectable attribute
collection = Collection("facts")
collection.load()

search_params = {
    "metric_type": "IP"
}

while True:

    print("what are you looking for?")
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
        metadata = json.loads(source["metadata"])
        if source["type"] == "pdf":
            print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]} located at {metadata["path"]}')
        if source["type"] == "web":
            print(f'   Web page: {metadata["source"]} scraped {metadata[ingest_date]}')

