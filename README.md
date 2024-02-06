# Concierge #

## Setup ##
git clone repo or extract zip  

`cd concierge` go into the cloned project directory

`python -m venv .` create a python virtual enviornment in the current directory

Linux: `source ./bin/activate` / Windows PowerShell: `.\Scripts\Activate.ps1` enter into the virtual environment

`pip install -r requirements.txt` install all dependencies

copy `.env.example` into a file named `.env` and set the paths to the PDF documents you wish to analyze and a folder on your computer that weaviate will use to store the database.

Create a docker bridge network for intra container networking: 
`docker network create -d bridge concierge`

Important: only pick on of these to choose your ollama start/setup:  
CPU only use the line below:  
`docker run -d --network concierge -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama`  

GPU support, use the line below:  
`docker run -d --network concierge --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama`

## Usage ##
`docker compose up` will start the docker container with the vector DB

`docker exec -it ollama ollama run mistral` will start the docker container with the model

`python loader.py` will load your documents into the database

`python prompter.py` will open the command line interface to query the documents

`python fact-check.py` will open the command line interface to ask true/false questions about the information in the documents

`docker compose down` will remove the vector DB container once you've finished using the tool
