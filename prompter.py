import os
# line below commented; future feature.
# import antigravity
from sentence_transformers import SentenceTransformer
import argparse
from configobj import ConfigObj
from tqdm import tqdm
from prompter_functions import LoadModel, InitCollection, GetContext, GetResponse

# TODO add collection as an option
# TODO make these be web inputs for streamlit
parser = argparse.ArgumentParser()
parser.add_argument("-t", "--task", required=True,
                    help="Required: What you want Concierge to do.")
parser.add_argument("-p", "--persona",
                    help="What personality or tone you want as the response")
parser.add_argument("-e", "--enhancers", nargs="*",
                    help="Comments to be added after the main response")
parser.add_argument("-f", "--file",
                    help="file to be used in prompt to Concierge")
args = parser.parse_args()


task = ConfigObj(f"prompter_config/tasks/{args.task}.concierge", list_values=False)

persona = None
if args.persona:
    persona = ConfigObj(f"prompter_config/personas/{args.persona}.concierge", list_values=False)

enhancers = None
if args.enhancers:
    enhancers = [ConfigObj(f"prompter_config/enhancers/{enhancer}.concierge", list_values=False) for enhancer in args.enhancers]

source_file = None
if args.file:
    if not os.path.exists(args.file):
        parser.error("The file %s does not exist!" % args.file)
    else:
        source_file = open(args.file, 'r')


### VARs ###
# TODO will want to make this a select later
references = 5

pbar = None
for progress in LoadModel():
    if not pbar:
        pbar = tqdm(
            unit="B",
            unit_scale=True,
            unit_divisor=1024
        )
    # slight hackiness to set the initial value if resuming a download or switching files
    if pbar.initial == 0 or pbar.initial > progress[0]:
        pbar.initial = progress[0]
    pbar.total = progress[1]
    pbar.n = progress[0]
    pbar.refresh()
if pbar:
    pbar.close()

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

collection = InitCollection()

search_params = {
    "metric_type": "IP"
}

while True:

    print(task['greeting'])
    user_input = input()

    context = GetContext(collection, references, user_input)

    print('\nResponding based on the following sources:')
    for source in context["sources"]:
        metadata = source["metadata"]
        if source["type"] == "pdf":
            print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]} located at {metadata["path"]}')
        if source["type"] == "web":
            print(f'   Web page: {metadata["source"]} scraped {metadata["ingest_date"]}')
    print("\n\n")

    if ('prompt' in task):
        response = GetResponse(
            context["context"], 
            task["prompt"], 
            user_input,
            None if not persona else persona["prompt"],
            None if not enhancers else [enhancer["prompt"] for enhancer in enhancers],
            None if not source_file else source_file.read()
        )

        print(response)
        print("\n\n")
    else:
        print("\n\n")
