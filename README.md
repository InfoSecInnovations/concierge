# Data Concierge AI #  
AI should be simple, safe, and amazing.  

## TL;DR: ##
Data Concierge AI (aka Concierge) is an AI system that works ONLY with the data you feed it. Your data, your prompts, everything are local to your instance.

## More details ##
Concierge is a local and modular RAG framework still in alpha.  

Built with simplicy and security in mind, it has some features we love -- and hope you do too!
* The quick install method is so easy.  (Note: fast install method is only supported on Linux and Windows. MacOS in development now.) 
* Loading data: Upload PDFs or point to a URL, click the ingest button... and the data is there for your use
* Tasks: you can change what the AI can do for you via dropdowns

## Dependencies ##  
Concierge requires the following to be available:
1. `python` (note: for all commands in documentation we will call the executable `python`. On your system you may need to use `python3`)
2. Docker (currently the vector database and natural language response engine are running in docker containers)
3. Docker compose (while frequently installed with docker, sometimes it's not. Docker compose files are how the docker containers are setup)  
   
Optional:  
If you want to use GPU acceleration (Concierge does NOT require this, but it will make responses dramatically faster), you must have the 
NVIDIA drivers correctly setup and running. Concierge will not install or make any adjustmetns to your driver configuration.  

Note: if you want to use GPU acceleration on a Windows host, you must use WSL2.  
More details here:  
https://docs.docker.com/desktop/gpu/

Refer to the documentation from NVIDIA for information on how to do this for your OS.

## System Requirements ##

It is unlikely you'll be able to run Concierge with less than 8GB RAM, at least 16GB is desirable.

If you're using Docker Desktop you need to make sure at least 4GB RAM is assigned to be used by containers. The default is half of the system memory, so if you have at least 8GB RAM and haven't modified your configuration it's likely you don't need to do anything.

You can get more tips for optimizing your installation here: https://opensearch.org/docs/latest/install-and-configure/install-opensearch/docker/#install-docker-and-docker-compose, however we have found that Concierge still runs without performing those modifications.

## Setup: quick install ##
git clone repo or extract zip. 

`cd concierge` go into the cloned project directory.

`python install.py` to launch the installer.  
Answer the questions and then the installer will ask if you are ready to make changes to the system.  
Answer "yes" and let the downloading begin!


## Setup: manual ##
If `install.py` did not work, follow these steps to setup your system. 

`python -m venv .` create a python virtual environment in the current directory.

Linux: `source ./bin/activate` / Windows PowerShell: `.\Scripts\Activate.ps1` enter into the virtual environment.

`pip install -r requirements.txt` install all dependencies.

Copy `.env.example` into a file named `.env` and set the folder on your computer that will contain the concierge data.

Set `OPENSEARCH_INITIAL_ADMIN_PASSWORD` to a strong password of your choice. You can evaluate password strength using https://lowe.github.io/tryzxcvbn/. Please note that in the current version of Concierge this isn't actually very secure due to it being stored in plaintext in the `.env` file! We will introduce better credential handling in future versions, the current way will become "dev/demo mode" for getting Concierge running quickly without proper security measures in place.

`docker compose up -d` will load the docker dependencies.

`docker compose -f docker-compose-gpu.yml up -d` will load the docker dependencies and use the GPU.

## Usage: launch script

From the cloned project directory simply run `launch.py`.

If the Docker container dependencies aren't found, you will be given the option to launch with CPU or GPU.

## Usage: manual ##
If `launch.py` did not work:

If you are not in the python virtual environment, please enter it by the correct method:  
Linux: `source ./bin/activate`  
Windows PowerShell: `.\Scripts\Activate.ps1`

To start the web UI, run the following command:

`python -m shiny run --launch-browser concierge_shiny/app.py`

If running for development you can use this command instead:

`python -m shiny run --reload --launch-browser concierge_shiny/app.py`

or use the Shiny for Python VSCode extension running from `concierge_shiny/app.py`. At the time of writing we have noticed an issue where the VSCode browser window doesn't automatically refresh and you have to copy/paste the URL from the console into it. Do this is after seeing the log `Application startup complete.` you still don't see anything in the VSCode browser.

## CLI ##

While we're currently more focused on the GUI element, we have provided some CLI scripts to be able to perform some functions without launching the web app.

To use them you can navigate to the `cli` subdirectory or append `cli.` to the script name from the parent directory.

Make sure you are running inside the venv.

Call commands like this: `python -m <script_name> <options>`. Use the `-h` or `--help` option to see what the options are.

Available commands:
- `loader`
- `web_loader`
- `prompter`
- `list_indices`
- `documents`
- `delete_index`

## Known issues

- `unknown shorthand flag: 'd' in -d` and/or you have the `docker-compose` command instead of `docker compose`. This indicates that you're using an older version of Docker than we support. The best course of action would be to install the latest version following instructions from here: https://docs.docker.com/engine/install/. However if you're unable to do this, you may be able to get the Concierge Docker requirements running using `docker-compose --file ./docker-compose.yml up`.
- on MacOS urllib3 gives a `NotOpenSSLWarning`, as far as we aware you can ignore this warning without issue.

## Want to get involved? ##

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) then our [Contribution Guide](CONTRIBUTING.md).
