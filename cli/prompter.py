import sys
import os
# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sentence_transformers import SentenceTransformer
import argparse
from configobj import ConfigObj
from tqdm import tqdm
from concierge_backend_lib.prompting import load_model, get_response
from concierge_backend_lib.opensearch import get_client, get_context

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--task", required=True,
                    help="Required: What you want Concierge to do.")
parser.add_argument("-i", "--index", required=True,
                    help="OpenSearch index containing the vectorized data.")
parser.add_argument("-p", "--persona",
                    help="What personality or tone you want as the response.")
parser.add_argument("-e", "--enhancers", nargs="*",
                    help="Comments to be added after the main response.")
parser.add_argument("-f", "--file",
                    help="file to be used in prompt to Concierge.")
args = parser.parse_args()

config_dir =  os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompter_config'))

task = ConfigObj(os.path.join(config_dir, 'tasks', f'{args.task}.concierge'), list_values=False)

persona = None
if args.persona:
    persona = ConfigObj(os.path.join(config_dir, 'personas', f'{args.persona}.concierge'), list_values=False)

enhancers = None
if args.enhancers:
    enhancers = [ConfigObj(os.path.join(config_dir, 'enhancers', f'{enhancer}.concierge'), list_values=False) for enhancer in args.enhancers]

source_file = None
if args.file:
    if not os.path.exists(args.file):
        parser.error("The file %s does not exist!" % args.file)
    else:
        source_file = open(args.file, 'r')

index_name = args.index

### VARs ###
# TODO will want to make this a select later
references = 5

pbar = None
for progress in load_model():
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
client = get_client()

while True:

    print(task['greeting'])
    user_input = input()

    context = get_context(client, index_name, references, user_input)

    print('\nResponding based on the following sources:')
    for source in context["sources"]:
        metadata = source["metadata"]
        if source["type"] == "pdf":
            print(f'   PDF File: page {metadata["page"]} of {metadata["source"]}')
        if source["type"] == "web":
            print(f'   Web page: {metadata["source"]} scraped {metadata["ingest_date"]}')
    print("\n\n")

    if ('prompt' in task):
        response = get_response(
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
