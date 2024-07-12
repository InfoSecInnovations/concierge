import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from configobj import ConfigObj
from tqdm import tqdm
from concierge_backend_lib.prompting import get_context, get_response
from concierge_backend_lib.ollama import load_model
from concierge_backend_lib.opensearch import get_client

parser = argparse.ArgumentParser()
parser.add_argument(
    "-t", "--task", required=True, help="What you want Concierge to do."
)
parser.add_argument(
    "-c",
    "--collection",
    required=True,
    help="Collection containing the vectorized data.",
)
parser.add_argument(
    "-p", "--persona", help="What personality or tone you want as the response."
)
parser.add_argument(
    "-e", "--enhancers", nargs="*", help="Comments to be added after the main response."
)
parser.add_argument("-f", "--file", help="File to be used in prompt to Concierge.")
args = parser.parse_args()

config_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "prompter_config")
)

task = ConfigObj(
    os.path.join(config_dir, "tasks", f"{args.task}.concierge"), list_values=False
)

persona = None
if args.persona:
    persona = ConfigObj(
        os.path.join(config_dir, "personas", f"{args.persona}.concierge"),
        list_values=False,
    )

enhancers = None
if args.enhancers:
    enhancers = [
        ConfigObj(
            os.path.join(config_dir, "enhancers", f"{enhancer}.concierge"),
            list_values=False,
        )
        for enhancer in args.enhancers
    ]

source_file = None
if args.file:
    if not os.path.exists(args.file):
        parser.error("The file %s does not exist!" % args.file)
    else:
        source_file = open(args.file, "r")

collection_name = args.collection

### VARs ###
# TODO will want to make this a select later
references = 5


def load_model_with_progress(model_name):
    pbar = None
    for progress in load_model(model_name):
        if not pbar:
            pbar = tqdm(
                desc=f"Loading {model_name} model",
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            )
        # slight hackiness to set the initial value if resuming a download or switching files
        if pbar.initial == 0 or pbar.initial > progress[0]:
            pbar.initial = progress[0]
        pbar.total = progress[1]
        pbar.n = progress[0]
        pbar.refresh()
    if pbar:
        pbar.close()


load_model_with_progress("mistral")

client = get_client()

while True:
    print(task["greeting"])
    user_input = input()

    context = get_context(client, collection_name, references, user_input)

    print("\nResponding based on the following sources:")
    for source in context["sources"]:
        doc_metadata = source["doc_metadata"]
        page_metadata = source["page_metadata"]
        if source["type"] == "pdf":
            print(
                f'   PDF File: page {page_metadata["page"]} of {doc_metadata["source"]}'
            )
        if source["type"] == "web":
            print(
                f'   Web page: {page_metadata["source"]} scraped {doc_metadata["ingest_date"]}, top level URL: {doc_metadata["source"]}'
            )
    print("\n\n")

    if "prompt" in task:
        response = get_response(
            context["context"],
            task["prompt"],
            user_input,
            None if not persona else persona["prompt"],
            None if not enhancers else [enhancer["prompt"] for enhancer in enhancers],
            None if not source_file else source_file.read(),
        )

        print(response)
        print("\n\n")
    else:
        print("\n\n")
