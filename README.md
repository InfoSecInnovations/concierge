# Shabti AI #  
AI should be simple, safe, and amazing.  

## TL;DR: ##
Shabti AI is an AI system that works ONLY with the data you feed it. Your data, your prompts, everything are local to your instance.

## More details ##
Shabti is a local and modular RAG framework still in alpha.  

Built with simplicy and security in mind, it has some features we love -- and hope you do too!
* The quick install method is so easy.
* Loading data: Upload PDFs or point to a URL, click the ingest button... and the data is there for your use.
* Tasks: you can change what the AI can do for you via dropdowns.

## Dependencies ##  

These versions are currently being used to develop Shabti, lower versions may work but are untested. See [Known Issues](#known-issues) for an older Docker Compose command which might work for you if you're unable to upgrade.

- **Docker >= 25.0.3** (currently the vector database and natural language response engine are running in docker containers). Check with `docker --version`.
- **Docker Compose >= 2.24.6** (while frequently installed with docker, sometimes it's not. Docker compose files are how the docker containers are setup). Check with `docker compose version`.  
   
Optional:  
If you want to use GPU acceleration (Shabti does NOT require this, but it will make responses dramatically faster), you must have the 
NVIDIA drivers correctly setup and running. Shabti will not install or make any adjustments to your driver configuration.  

Note: if you want to use GPU acceleration on a Windows host, you must use WSL2.  
More details here:  
https://docs.docker.com/desktop/gpu/

Refer to the documentation from NVIDIA for information on how to do this for your OS.

## System Requirements ##

It is unlikely you'll be able to run Shabti with less than 16GB RAM.

If you're using Docker Desktop you need to make sure at least 8GB RAM is assigned to be used by containers. The default is half of the system memory, so if you have at least 16GB RAM and haven't modified your configuration it's likely you don't need to do anything.

You should perform the following system configuration steps according to your Operating System: https://opensearch.org/docs/latest/install-and-configure/install-opensearch/docker/#install-docker-and-docker-compose, otherwise you may not be able to run the OpenSearch container Shabti depends on.

## Setup

Shabti now has a visual configurator which we hope you will like a lot more than the previous text-based one. Just go to the release you wish to install and download the executable for your Operating System. Please let us know if you're using a different Operating System, it may be possible for us to make a build for it. You can also use the development version.

Launch the executable and visit the address indicated in your web browser. Select your desired options and click "Start Installation!".

Note that the installer launches all the requirements for you, you generally won't need to use the "Launch Shabti" button. Docker will keep everything running for you and you will be able to access Shabti without going via the Configurator once installed.

## Usage

Once you have completed the installation process, Shabti will be running on localhost:15130 or the host and port you selected during setup. It can take a little while for the containers to be ready after install or relaunch, especially on the first launch as the API needs to pull the embeddings model.

## Using Security Features

Currently Shabti is using self-signed HTTPS certificates to secure connections. In the future we will add more options to use your own certificates and/or install the generated ones. For the moment you should just ignore the warnings in the web browser, in some browsers you have to expand the warning first in order to proceed.

If you chose to enable security during installation, you will have to configure the Keycloak instance we have provided to set up some users with the appropriate permissions.

Start by opening up https://localhost:8443 in your browser. Here you should see the Keycloak login page, input the username `admin` and the password you set during installation.

You should refer to the [Keycloak documentation](https://www.keycloak.org/docs/latest/server_admin/index.html) to find out how to configure the type of login you wish to support. You can enable a variety of social network logins, OpenID, LDAP or just username and password.

The configuration we have supplied has already created the super admin user (the one you used to connect to Keycloak above), and a realm called `shabti` with some roles the provide various levels of access to Shabti. Make sure to configure logins and users in this realm and not the master realm.

The super admin user only serves to administrate the Keycloak instance, they do not have any permissions to access Shabti as a user.

If using authorization, there are shared and private collections. A private collection can only be viewed by the user who created it, a shared collection can be viewed by any user with required role. In the future we will add options to switch a collection from private to shared. If you need more specific permissions you can configure those in the `shabti-auth` client using the resources that represent collections.

### Roles

The roles that grant access to Shabti collections can be found within the `shabti-auth` client in the `shabti` realm.

- `admin` - can do everything including viewing, updating and deleting other users' private collections. This is different from the super admin user in the master realm.
- `private_collection` - can create and manage personal collections not accessible by other users (except the admin).
- `shared_read` - can query the shared collections, but not modify in any way.
- `shared_read_write` - has full control of shared collections.

### Creating users with roles

If you want to quickly try out some of the options, you can go ahead and create some users in the Keycloak admin console and assign the above roles to them. We'd recommend using a more secure method of user registration for a production environment.

Make sure to log in as the super admin account and switch the realm to "shabti" in the admin UI.

Select the Users view in the menu.

Click "Add user" and assign them a username, click "Create".

If you're creating this user for testing purposes you can use the "Credentials" tab to set a password, and you can even toggle off "Temporary" so you won't have to change it when logging in.

Go to the "Role mapping" tab, click "Assign role", make sure "Filter by clients" is selected, and locate the roles prefixed with `shabti-auth`. Assign the desired roles to your user.

You will now be able to use the username and password you created to log into the web app.

If you need to switch user you may need to revoke the session of the currently logged in user, which is available in the "Sessions" tab for that user, otherwise clicking the login button may just automatically log you in with the same user again.

## Troubleshooting

### Shabti API is down

Check the Docker logs for the container called `shabti`. If you don't see a log that says "Application startup complete", keep waiting, it may still be loading the embeddings model.

### Shabti Web UI is broken or blank

Perform an "Empty Cache and Hard Reload" on the page. Depending on your browser you may need to open the dev tools to do this.

### Blank response when using the prompter

Check the Docker logs for the container called `ollama`. If you see a warning about Ollama not having enough memory allocated, you must increase the amount of RAM available to Docker.

### Other issues

Please create an issue [here](https://github.com/InfoSecInnovations/concierge/issues). Check the Docker logs of the containers inside the `shabti` compose stack for any errors or warnings and include those in your report. Also include any errors displayed in the Web UI or the console during the install process.

## Setup: development environment

### Dependencies

The ones listed at the top of this page, and:
- **Python 3.12** the application code is in Python so unless you intend to only run inside Docker, you'll need this
- **Bun 1.2.1** the configurator is written in JavaScript that depends on the Bun runtime. Bun allows us to effortlessly build the executable files for each Operating System.

### Installation

git clone repo or extract zip. 

`cd shabti` go into the cloned project directory.

do `bun install` in the repository root. This will set up all the JavaScript projects.

`cd shabti_configurator` to go to the configurator directory.

`bun run dev_install` will launch the web server in dev mode which provides additional install and launch options compared to the distributed executable. Once the server is running go to http://localhost:3000 to see the configuration options. Click the "Install Development Configuration" button to install the dependencies in a way which will allow you to run local code with your changes.

## Usage: development environment

Install using the instructions above.

Make sure to read the [Contribution Guide](CONTRIBUTING.md) to find out more about coding style enforcement and commit etiquette!

### Launch from Configurator

As well as installing, the web-based Configurator gives you some options to launch Shabti.

The "Launch Shabti" button shouldn't be used to test local changes to the Python scripts as this uses the image from the Docker Hub and not your local files.

"Launch X Locally (Docker)" will build the local files into a Docker image and put it up in a container mimicking the production environment. You should always try your code here before submitting a PR as there are some minor differences with how the components communicate with each other within Docker compared to running the code locally. The first build can be slow, but the Python dependencies will be cached making subsequent builds much faster.

"Launch X Locally (Python)" is a straightforward way to run the Python code directly from your local files.

### Launch API in dev mode with reloading

- Navigate to `docker_containers/shabti_api`
- Enable the virtual environment
- Navigate to the `app` subdirectory
- `fastapi dev app.py`

You will see in the command line that the Swagger UI is available, this is really useful for testing out the REST API functions.

## CLI ##

Shabti now ships with a standalone executable for the Command Line Interface and the syntax has been completely revamped. We will add proper documentation for this, but you can call the executable with the `-h` flag to see which commands exist and how to use them. The CLI executable must be in the same directory as the main executable and will only work after you've installed Shabti.

## Known Issues

- Startup of the Shabti API service can be quite slow, this appears to be especially so when running in Docker for some reason. We believe it's due to one of the AI related dependencies, we will review this problem at some point as there may be alternative frameworks we could use.

## Want to get involved? ##

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) then our [Contribution Guide](CONTRIBUTING.md).
