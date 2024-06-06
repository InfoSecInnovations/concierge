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

These versions are currently being used to develop Concierge, lower versions may work but are untested. See [Known Issues](#known-issues) for an older Docker Compose command which might work for you if you're unable to upgrade.

- **Python >= 3.12** (note: for all commands in documentation we will call the executable `python`. On your system you may need to use `python3`, you can use the `python-is-python3` package to configure the `python` command on Linux). Check with `python --version`.
- **Docker >= 25.0.3** (currently the vector database and natural language response engine are running in docker containers). Check with `docker --version`.
- **Docker Compose >= 2.24.6** (while frequently installed with docker, sometimes it's not. Docker compose files are how the docker containers are setup). Check with `docker compose version`.  
   
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

## Setup

### Quick install

git clone repo or extract zip. 

`cd concierge` go into the cloned project directory.

`python install.py` to launch the installer.

Answer the questions and then the installer will ask if you are ready to make changes to the system.  
Answer "yes" and let the downloading begin!

### Manual install

If `install.py` did not work, follow these steps to setup your system. 

Copy `.env.example` into a file named `.env`

Set `DOCKER_VOLUME_DIRECTORY` to the volume on your computer where you wish Concierge data to be stored

`docker compose up -d` will start Concierge and its dependencies in Docker.

`docker compose -f docker-compose-gpu.yml up -d` will start Concierge and its dependencies in Docker and use the GPU.

## Usage

Once you have set up the Docker containers using one of the methods above, Concierge will be running on localhost:8000. It can take a couple of minutes for the containers to be ready after install or relaunch.

If the containers aren't running properly you can try using `python launch.py` to launch them again.

## Update to new release

Pull or download the latest version of the repository.

### Quick install

Running `install.py` should be able to take care of upgrading your configuration.

If you already have a language model downloaded and you didn't remove the Concierge volume you can use ctrl+C to skip the model pull in the last stage of the install (although you may want to get the latest version).

### Manual update

`docker compose -f <docker-compose-file.yml> pull` will grab the latest versions of the Docker containers.

`docker compose -f <docker-compose-file.yml> build` will rebuild the Docker container with the latest version of Concierge.

Now you can reconfigure the `.env` file and relaunch the containers like in the Manual install step.

## Setup: development environment

### Quick install

Follow the same instructions as for production, except use `install_dev.py` instead of `install.py`

### Manual install

Configure the `.env` file as above.

Set `ENVIRONMENT` to `development`

`python -m venv .` create a python virtual environment in the current directory.

Linux: `source ./bin/activate` / Windows PowerShell: `.\Scripts\Activate.ps1` enter into the virtual environment.

`pip install -r requirements.txt -r dev_requirements.txt` install all dependencies.

`docker compose -f docker-compose-dev.yml up -d` will load the docker dependencies for developers.

`docker compose -f docker-compose-dev-gpu.yml up -d` will load the docker dependencies for developers and use the GPU.

## Usage: development environment

Complete one of the installation methods above.

Make sure to read the [Contribution Guide](CONTRIBUTING.md) to find out more about coding style enforcement and commit etiquette!

### Visual Studio Code

Install Shiny for Python VSCode extension.

Run Shiny for Python VSCode extension from `concierge_shiny/app.py`. 

At the time of writing we have noticed an issue where the VSCode browser window doesn't automatically refresh and you have to copy/paste the URL from the console into it. Do this is after seeing the log `Application startup complete.` you still don't see anything in the VSCode browser.

You can also access the URL by pasting it into another browser.

### Launch script

From the cloned project directory simply run `launch_dev.py`.

If the Docker container dependencies aren't found, you will be given the option to launch with CPU or GPU.

### Manual launch

If the above methods did not work:

If you are not in the python virtual environment, please enter it by the correct method:  
Linux and MacOS: `source ./bin/activate`  
Windows PowerShell: `.\Scripts\Activate.ps1`

To start the web UI, run the following command:

`python -m shiny run --reload --launch-browser concierge_shiny/app.py`

## Update to new release: development environment

### Quick install

Follow the same instructions as for production, except use `install_dev.py` instead of `install.py`

### Manual update

Use `docker compose pull -f <docker-compose-file.yml>` to update the Docker containers.

Follow Manual install steps above.

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
- on MacOS urllib3 gives a `NotOpenSSLWarning`, as far as we aware you can ignore this warning without issue. This should only be present when using the development environment.

## Want to get involved? ##

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) then our [Contribution Guide](CONTRIBUTING.md).
