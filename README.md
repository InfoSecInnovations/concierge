# Concierge #  
AI should be simple, safe, and amazing.

## Setup: `install.py` ##
git clone repo or extract zip. 

`cd concierge` go into the cloned project directory.

`python install.py` to launch the installer.  
Answer the questions and then the installer will ask if you are ready to make changes to the system.  
Answer "Y" and let the downloading begin!


## Setup: manual ##
If `install.py` did not work, follow these steps to setup your system. 

`python -m venv .` create a python virtual enviornment in the current directory.

Linux: `source ./bin/activate` / Windows PowerShell: `.\Scripts\Activate.ps1` enter into the virtual environment.

`pip install -r requirements.txt` install all dependencies.

copy `.env.example` into a file named `.env` and set the folder on your computer that will contain the concierge data.

`docker compose up -d` will load the docker dependencies.

`docker compose -f docker-compose-gpu.yml up -d` will load the docker dependencies and use the GPU.

## Usage: ##
If you are not in the python virtual enviornment, please enter it by the correct method:  
Linux: `source ./bin/activate`  
Windows PowerShell: `.\Scripts\Activate.ps1`

To start the web UI, run the following command:  
`streamlit run Concierge.py`
