from script_builder.util import require_admin, pip_loader
from script_builder.argument_processor import ArgumentProcessor
from concierge_installer.arguments import install_arguments
from concierge_installer.functions import docker_compose_helper
import os
import shutil
import subprocess

require_admin()

argument_processor = ArgumentProcessor(install_arguments)

argument_processor.init_args()

# message:
print("\n\n\nConcierge: AI should be simple, safe, and amazing.\n\n\n")

# If Docker isn't present, there's no point in proceeding
if not shutil.which("docker"):
    print("Docker isn't installed. You will need it to be able to proceed, please install Docker or use a machine which has it installed!")
    exit()

# check if docker is running
process_info = subprocess.run(["docker", "info"], stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
# if it's not running we can't check anything docker related
if process_info.returncode == 1:
    print("Docker isn't running.")
    print("This script requires the Docker daemon to be running. Please start it and rerun the script once it's up and running.")
    exit()

# Check if Concierge is already configured
if os.path.isfile(".env"):
    concierge_root = ""
    # read .env file manually because we don't necessarily have the pip requirements installed yet
    with open(".env") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("DOCKER_VOLUME_DIRECTORY="):
                concierge_root = stripped.replace("DOCKER_VOLUME_DIRECTORY=", "")
                break

    # if the Concierge docker directory is configured, we take that to mean it has previously been installed
    if concierge_root:

        print("Concierge instance discovered.")
        print("This script can help reset your system for a re-install.\n")

        # option to remove volumes directory
        concierge_volumes = os.path.join(concierge_root, "volumes")
        print("Removing the Concierge volumes will delete all ingested data and any language models you downloaded.")
        print("Remove Concierge volumes?")
        approve_to_delete = input(f"Type 'yes' to delete {concierge_volumes} or press enter to skip: ")
        print("\n")
        if approve_to_delete == "yes":
            shutil.rmtree(concierge_volumes)

        # check docker containers
        print("The following docker containers were discovered:")
        subprocess.run(["docker", "container", "ls", "--all", "--format", "{{.Names}}"])

        print("\nWould you like to have the installer remove any for you?")
        containers_to_remove = input("Please give a space separated list of the containers you would like removed or press enter to skip: ")
        print("\n")

        if containers_to_remove != "":
            subprocess.run(["docker", "container", "rm", containers_to_remove], stdout = subprocess.DEVNULL)

        # check docker networks
        print("The following docker networks were discovered:")
        subprocess.run(["docker", "network", "ls", "--format", "{{.Name}}"])

        print("\nWould you like to have the installer remove any for you?")
        networks_to_remove = input("Please give a space separated list of the networks you would like removed or press enter to skip: ")
        print("\n")

        if networks_to_remove != "":
            subprocess.run(["docker", "network", "rm", networks_to_remove], stdout = subprocess.DEVNULL)

print("Welcome to the Concierge installer.")
print("Just a few configuration questions and then some download scripts will run.")
print("Note: you can just hit enter to accept the default option.\n\n")

argument_processor.prompt_for_parameters()

print("Concierge setup is almost complete.\n")
print("If you want to speed up the deployment of future Concierge instances with these exact options, save the command below.\n")
print("After git clone or unzipping, run this command and you can skip all these questions!\n\n")
print("\ninstall.py" + argument_processor.get_command_parameters() + "\n\n\n")

print("About to make changes to your system.\n")
# TODO make a download size variable & update based on findings
#print("Based on your selections, you will be downloading aproximately X of data")
#print("Depending on network speed, this may take a while")
print("No changes have yet been made to your system. If you stop now or answer no, nothing will have changed.")
ready_to_rock = input("Ready to apply settings and start downloading? [Y/n]: ")

if ready_to_rock == "Y":
    # no further input is needed. Let's get to work.
    print("installing...")

    # setup .env (needed for docker compose files)
    env_file = open(".env", "w")
    # write .env info needed
    env_file.write("DOCKER_VOLUME_DIRECTORY=" + argument_processor.parameters["docker_volumes"])
    env_file.close()

    pip_loader()

    # docker compose
    if argument_processor.parameters["compute_method"] == "GPU":
        docker_compose_helper("GPU")
    elif argument_processor.parameters["compute_method"] == "CPU":
        docker_compose_helper("CPU")
    else:
        #need to do input check to prevent this condition (and others like it)
        print("You have selected an unknown/unexpected compute method.")
        print("you will need to run the docker compose file manually")
        exit()

    # ollama model load
    returncode = subprocess.run(["docker", "exec", "-it", "ollama", "ollama", "run", argument_processor.parameters["language_model"]])

else:
    print("Install cancelled. No changes were made. Have a nice day! :-)\n\n")
    exit()