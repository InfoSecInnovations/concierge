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

Concierge now has a visual configurator which we hope you will like a lot more than the previous text-based one. Just go to the release you wish to install and download the executable for your Operating System. Please let us know if you're using a different Operating System, it may be possible for us to make a build for it. You can also use the development version.

Launch the executable and visit the address indicated in your web browser. Select your desired options and click "Start Installation!".

Note that the installer launches all the requirements for you, you generally won't need to use the "Launch Concierge" button. Docker will keep everything running for you and you will be able to access Concierge without going via the Configurator once installed.

## Usage

Once you have completed the installation process, Concierge will be running on localhost:15130 or the host and port you selected during setup. It can take a couple of minutes for the containers to be ready after install or relaunch.

## Configuring Authentication and Authorization

If you chose to enable login and access controls during installation, you will have to configure the Keycloak instance we have provided to set up some users with the appropriate permissions.

Start by opening up https://localhost:8443 in your browser. Here you should see the Keycloak login page, input the username `admin` and the password you set during installation.

You should refer to the [Keycloak documentation](https://www.keycloak.org/docs/latest/server_admin/index.html) to find out how to configure the type of login you wish to support. You can enable a variety of social network logins, OpenID, LDAP or just username and password.

The configuration we have supplied has already created the super admin user (the one you used to connect to Keycloak above), and a realm called `concierge` with some roles the provide various levels of access to Concierge. Make sure to configure logins and users in this realm and not the master realm.

The super admin user only serves to administrate the Keycloak instance, they do not have any permissions to access Concierge as a user.

If using authorization, there are shared and private collections. A private collection can only be viewed by the user who created it, a shared collection can be viewed by any user with required role. In the future we will add options to switch a collection from private to shared. If you need more specific permissions you can configure those in the `concierge-auth` client using the resources that represent collections.

### Roles

The roles that grant access to Concierge collections can be found within the `concierge-auth` client in the `concierge` realm.

- `admin` - can do everything including viewing, updating and deleting other users' private collections. This is different from the super admin user in the master realm.
- `private_collection` - can create and manage personal collections not accessible by other users (except the admin).
- `shared_read` - can query the shared collections, but not modify in any way.
- `shared_read_write` - has full control of shared collections.

### Creating users with roles

If you want to quickly try out some of the options, you can go ahead and create some users in the Keycloak admin console and assign the above roles to them. We'd recommend using a more secure method of user registration for a production environment.

Make sure to log in as the super admin account and switch the realm to "concierge" in the admin UI.

Select the Users view in the menu.

Click "Add user" and assign them a username, click "Create".

If you're creating this user for testing purposes you can use the "Credentials" tab to set a password, and you can even toggle off "Temporary" so you won't have to change it when logging in.

Go to the "Role mapping" tab, click "Assign role", make sure "Filter by clients" is selected, and locate the roles prefixed with `concierge-auth`. Assign the desired roles to your user.

You will now be able to use the username and password you created to log into the web app.

If you need to switch user you may need to revoke the session of the currently logged in user, which is available in the "Sessions" tab for that user, otherwise clicking the login button may just automatically log you in with the same user again.

## Setup: development environment

### Dependencies

The ones listed at the top of this page, and:
    - **Python 3.12** the application code is in Python so unless you intend to only run inside Docker, you'll need this
    - **Bun 1.2.1** the configurator is written in JavaScript that depends on the Bun runtime. Bun allows us to effortlessly build the executable files for each Operating System.

### Installation

git clone repo or extract zip. 

`cd concierge` go into the cloned project directory.

You should not create a virtual environment as the installer will handle it for you.

`cd bun_installer` to go into the subdirectory containing all the Bun scripts for the configurator.

`bun install` to add all dependencies.

`bun run dev_install` will launch the web server in dev mode which provides additional install and launch options compared to the distributed executable. Once the server is running go to http://localhost:3000 to see the configuration options. Click the "Install Development Configuration" button to install the dependencies in a way which will allow you to run local code with your changes.

## Usage: development environment

Install using the instructions above.

Make sure to read the [Contribution Guide](CONTRIBUTING.md) to find out more about coding style enforcement and commit etiquette!

### Launch from Configurator

As well as installing, the web-based Configurator gives you some options to launch Concierge.

The "Launch Concierge" button shouldn't be used to test local changes to the Python scripts as this uses the image from the Docker Hub.

"Launch Local Code (Docker)" will build the local files into a Docker image and put it up in a container mimicking the production environment. You should always try your code here before submitting a PR as there are some minor differences with how the components communicate with each other within Docker compared to running the code locally. The first build can be slow, but the Python dependencies will be cached making subsequent builds much faster.

"Launch Local Code (Python)" is a straightforward way to 

### Visual Studio Code

Install Shiny for Python VSCode extension.

Run Shiny for Python VSCode extension from `concierge_shiny/app.py`.

You can also access the URL by pasting it into another browser.

At this time it doesn't seem to be possible to use HTTPS while launching from VSCode.

#### With authentication

Authentication doesn't play very nicely with VSCode, however it is still possible to use it.

- Manually configure the port used by Shiny in the extension configuration to match the one you chose during install.
- Access the web app through your browser, not through the built-in VSCode one.

This does offer the advantage of hot reloading and being able to use the debugger while testing authentication.

## CLI ##

While we're currently more focused on the GUI element, we have provided some CLI scripts to be able to perform some functions without launching the web app. We haven't yet included these in our automated test coverage, so please let us know if you're trying to use them and having issues.

One notable feature is that the `loader` script loads an entire directory of documents which the GUI is currently unable to do.

To use them you can navigate to the `cli` subdirectory.

Make sure you are running inside the virtual environment created during installation.

Call commands like this: `python -m <script_name> <options>`. Use the `-h` or `--help` option to see what the options are.

If your instance of Concierge has RBAC enabled the CLI runs with full admin privileges, so use with care! If there's demand for it we may consider adding proper login to be able to use the CLI with a user account.

Available commands:
- `loader`
- `web_loader`
- `prompter`
- `list_collections`
- `list_documents`
- `delete_collection`
- `delete_document`

## Want to get involved? ##

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) then our [Contribution Guide](CONTRIBUTING.md).
