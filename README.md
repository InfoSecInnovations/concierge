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

The provided install scripts perform a lot of automated cleanup and ensure that all the components are configured correctly to work together. However as this is an open source project you could create your own installation using the contents of this repository.

You no longer need to clone this repository to run Concierge.

> [!TIP]
> Pay attention to the use of dashes and underscores in the commands!

Run the following while not being in a virtual environment. This command will create the virtual environment and run the installer from within it.

`python -m pip install launch-concierge`

`python -m launch_concierge.install`

Answer the questions and then the installer will ask if you are ready to make changes to the system.  
Answer "yes" and let the installation begin!
There may be additional questions during the installation depending on the options you selected.

Please note that this package isn't the Concierge app itself, it's just a utility that helps you configure the environment and launch the correct Docker Compose file based on your choices, so it shouldn't be hugely risky to download it without using a virtual environment.

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

## Usage

Once you have completed the installation process above, Concierge will be running on localhost:15130 or the host and port you selected during setup. It can take a couple of minutes for the containers to be ready after install or relaunch.

## Update to new release

If running a version prior to 0.3.0 you should delete the files you cloned from the repository, remove the related Docker containers and proceed with a fresh install following the instructions above.

### Without virtual environment

`python -m pip install launch-concierge --upgrade`

`python -m launch_concierge.install`

### With virtual environment

Activate the environment if not already done

`pip install launch-concierge --upgrade`

`install_concierge`

## Setup: development environment

git clone repo or extract zip. 

`cd concierge` go into the cloned project directory.

You should not create a virtual environment as the script below will handle it for you.

`python install_dev.py` to launch the installer (same steps as the user installer).

## Usage: development environment

Complete one of the installation methods above.

Make sure to read the [Contribution Guide](CONTRIBUTING.md) to find out more about coding style enforcement and commit etiquette!

### Visual Studio Code

Install Shiny for Python VSCode extension.

Run Shiny for Python VSCode extension from `concierge_shiny/app.py`.

You can also access the URL by pasting it into another browser.

At this time it doesn't seem to be possible to use HTTPS while launching from VSCode.

#### With authentication

Authentication doesn't play very nicely with VSCode, however it is still possible to use it.

- Manually configure the port used by Shiny in the extension configuration to match the one you chose during install.
- Access the web app through your browser, not through the built-in VSCode one.

This does offer the advantage of being able to use the debugger while testing authentication.

### Launch script

From the cloned project directory simply run `launch_dev.py`.

You will be given the option to launch with CPU or GPU.

`python launch_local.py` will build and launch the code in a Docker container as if it were the production environment, this allows you to locally test interactions between the containers.

## Update to new release: development environment

Clone the latest version of the repo.

Repeat the process used during install.

## CLI ##

> [!WARNING]
> We haven't yet updated the CLI scripts to work with authentication and authorization, it's likely some of them are broken.

While we're currently more focused on the GUI element, we have provided some CLI scripts to be able to perform some functions without launching the web app.

One notable feature is that the `loader` script loads an entire directory of documents which the GUI is currently unable to do.

To use them you can navigate to the `cli` subdirectory or append `cli.` to the script name from the parent directory.

Make sure you are running inside the virtual environment created during installation.

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
