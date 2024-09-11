# Data Concierge AI #  
AI should be simple, safe, and amazing.  

## TL;DR: ##
Data Concierge AI (aka Concierge) is an AI system that works ONLY with the data you feed it. Your data, your prompts, everything are local to your instance.

## More details ##
Concierge is a local and modular RAG framework still in alpha.  

Built with simplicy and security in mind, it has some features we love -- and hope you do too!
* The quick install method is so easy.
* Loading data: Upload PDFs or point to a URL, click the ingest button... and the data is there for your use.
* Tasks: you can change what the AI can do for you via dropdowns.

## Dependencies ##  

These versions are currently being used to develop Concierge, lower versions may work but are untested. See [Known Issues](#known-issues) for an older Docker Compose command which might work for you if you're unable to upgrade.

- **Python >= 3.12** (note: for all commands in documentation we will call the executable `python`. On your system you may need to use `python3`, you can use the `python-is-python3` package to configure the `python` command on Linux). Check with `python --version`.
- **Docker >= 25.0.3** (currently the vector database and natural language response engine are running in docker containers). Check with `docker --version`.
- **Docker Compose >= 2.24.6** (while frequently installed with docker, sometimes it's not. Docker compose files are how the docker containers are setup). Check with `docker compose version`.  
   
Optional:  
If you want to use GPU acceleration (Concierge does NOT require this, but it will make responses dramatically faster), you must have the 
NVIDIA drivers correctly setup and running. Concierge will not install or make any adjustments to your driver configuration.  

Note: if you want to use GPU acceleration on a Windows host, you must use WSL2.  
More details here:  
https://docs.docker.com/desktop/gpu/

Refer to the documentation from NVIDIA for information on how to do this for your OS.

## System Requirements ##

It is unlikely you'll be able to run Concierge with less than 8GB RAM, at least 16GB is desirable.

If you're using Docker Desktop you need to make sure at least 4GB RAM is assigned to be used by containers. The default is half of the system memory, so if you have at least 8GB RAM and haven't modified your configuration it's likely you don't need to do anything.

You should perform the following system configuration steps according to your Operating System: https://opensearch.org/docs/latest/install-and-configure/install-opensearch/docker/#install-docker-and-docker-compose, otherwise you may not be able to run the OpenSearch container Concierge depends on.

## Setup

The provided install scripts perform a lot of automated cleanup and ensure that all the components are configured correctly to work together, so we strongly recommend you use these instead of attempting the manual install. However if you need to customize the Docker environment the manual steps may help you find what you need to be able to do so.

### Quick install (Recommended)

You no longer need to clone this repository.

You have a couple of options depending on your preferences.

> [!TIP]
> Pay attention to the use of dashes and underscores in the commands!

If you're not concerned about using a virtual environment you can just use the 2 commands below in the directory of your choosing:

`python -m pip install launch-concierge`

`python -m launch_concierge.install`

If you prefer to keep things contained in a virtual environment you can use the 4 commands below:

`python -m venv .`

`.\scripts\activate.ps1` or `source bin/activate` depending on your Operating System

`pip install launch-concierge`

`install_concierge`

Answer the questions and then the installer will ask if you are ready to make changes to the system.  
Answer "yes" and let the downloading begin!

Please note that the package isn't the Concierge app itself, it's just a utility that helps you configure the environment and launch the correct Docker Compose file based on your choices, so it shouldn't be hugely risky to download it without using a virtual environment.

### Manual install

If you would prefer to configure and launch the app without going through our utility script it is also fairly straightforward:

Create a file called `.env` following the template of `.env.example` in this repository.

From `concierge_packages/launcher/src/launch_concierge/docker_compose` copy `docker_compose_dependencies`.

From the same directory, if you wish to use the CPU only, copy `docker-compose.yml`, if you wish to use GPU acceleration where available, copy `docker-compose-gpu.yml` instead.

To launch the CPU compose file use `docker compose up -d`, to launch the GPU version you need to use `docker compose -f docker-compose-gpu.yml up -d`.

## Usage

Once you have set up the Docker containers using one of the methods above, Concierge will be running on localhost:15130 or the port you selected during setup. It can take a couple of minutes for the containers to be ready after install or relaunch.

## Update to new release

If running a version prior to 0.3.0 you should delete the files you cloned from the repository, remove the related Docker containers and proceed with a fresh install following the instructions above.

### Quick install (Recommended)

#### Without virtual environment

`python -m pip install launch-concierge --upgrade`

`python -m launch_concierge.install`

#### With virtual environment

Activate the environment if not already done

`pip install launch-concierge --upgrade`

`install_concierge`

### Manual install

Make sure to grab the latest version of the Docker Compose files.

`docker compose pull` or `docker compose -f docker-compose-gpu.yml pull` will get the latest versions of the containers being used.

Then you can simply launch the containers again using the command from the install step.

## Setup: development environment

git clone repo or extract zip. 

### Quick install (Recommended)

`cd concierge` go into the cloned project directory.

You should not create a virtual environment as the script below will handle it for you.

`python install_dev.py` to launch the installer (same steps as the user installer).

### Manual install

Configure the `.env` file like in the user install.

Set `ENVIRONMENT` to `development`

`python -m venv .` create a python virtual environment in the current directory.

Linux: `source ./bin/activate` / Windows PowerShell: `.\Scripts\Activate.ps1` enter into the virtual environment.

`pip install -r requirements.txt -r dev_requirements.txt` install all dependencies.

`pre-commit install` install the linting script that hooks into the commit command.

`docker compose -f docker-compose-dev.yml up -d` will load the docker dependencies for developers.

`docker compose -f docker-compose-dev-gpu.yml up -d` will load the docker dependencies for developers and use the GPU.

If you want to build the code to a Docker container to simulate the production environment you can use the `docker-compose-local.yml` or `docker-compose-gpu-local.yml` files. On initial launch and when you've made changes to the code you'll need to use `docker compose -f <docker-compose-file.yml> build` to update the container and then launch the compose file again.

## Usage: development environment

Complete one of the installation methods above.

Make sure to read the [Contribution Guide](CONTRIBUTING.md) to find out more about coding style enforcement and commit etiquette!

### Visual Studio Code

Install Shiny for Python VSCode extension.

Run Shiny for Python VSCode extension from `concierge_shiny/app.py`. 

At the time of writing we have noticed an issue where the VSCode browser window doesn't automatically refresh and you have to copy/paste the URL from the console into it. Do this if after seeing the log `Application startup complete.` you still don't see anything in the VSCode browser.

You can also access the URL by pasting it into another browser.

### Launch script

From the cloned project directory simply run `launch_dev.py`.

If the Docker container dependencies aren't found, you will be given the option to launch with CPU or GPU.

`python launch_local.py` will build and launch the code in a Docker container as if it were the production environment.

### Manual launch

If the above methods did not work:

If you are not in the python virtual environment, please enter it by the correct method:  
Linux and MacOS: `source ./bin/activate`  
Windows PowerShell: `.\Scripts\Activate.ps1`

To start the web UI, run the following command:

`python -m shiny run --reload --launch-browser concierge_shiny/app.py`

## Update to new release: development environment

Clone the latest version of the repo.

### Quick install

Repeat the process used during install.

### Manual update

Use `docker compose -f <docker-compose-file.yml> pull` to update the Docker containers.

Repeat the process used during install.

## CLI ##

While we're currently more focused on the GUI element, we have provided some CLI scripts to be able to perform some functions without launching the web app.

One notable feature is that the `loader` script loads an entire directory of documents which the GUI is currently unable to do.

To use them you can navigate to the `cli` subdirectory or append `cli.` to the script name from the parent directory.

Make sure you are running inside the venv.

Call commands like this: `python -m <script_name> <options>`. Use the `-h` or `--help` option to see what the options are.

Available commands:
- `loader`
- `web_loader`
- `prompter`
- `list_collections`
- `list_documents`
- `delete_collection`
- `delete_document`

## Known issues

- `unknown shorthand flag: 'd' in -d` and/or you have the `docker-compose` command instead of `docker compose`. This indicates that you're using an older version of Docker than we support. The best course of action would be to install the latest version following instructions from here: https://docs.docker.com/engine/install/. However if you're unable to do this, you may be able to get the Concierge Docker requirements running using `docker-compose --file ./docker-compose.yml up`.
- on MacOS urllib3 gives a `NotOpenSSLWarning`, as far as we aware you can ignore this warning without issue. This should only be present when using the development environment.

## Want to get involved? ##

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) then our [Contribution Guide](CONTRIBUTING.md).
