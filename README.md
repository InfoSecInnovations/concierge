# Concierge #  
AI should be simple, safe, and amazing.

## Setup ##
git clone repo or extract zip. 

`cd concierge` go into the cloned project directory.

`python -m venv .` create a python virtual enviornment in the current directory.

Linux: `source ./bin/activate` / Windows PowerShell: `.\Scripts\Activate.ps1` enter into the virtual environment.

`pip install -r requirements.txt` install all dependencies.

copy `.env.example` into a file named `.env` and set the paths to the PDF documents you wish to analyze and a folder on your computer that will contain the vector database.

## Usage ##
`docker compose up -d` will load the docker dependencies.

`docker compose -f docker-compose-gpu.yml up -d` will load the docker dependencies and use the GPU.

`python loader.py` will load your documents into the database.

`python web-loader.py <url>` will scrape a website and load it into the database. 

`python prompter.py` will open the command line interface to query the documents. `python prompter.py -h` will tell you the parameters expected by the script.

`docker compose down` will shut down the docker dependencies.

`docker compose -f docker-compose-gpu.yml down` will shut down the docker dependencies if you started them with the GPU.
