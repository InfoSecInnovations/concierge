import argparse
import os
import requests
import subprocess
import sys
from os.path import abspath
from subprocess import run
from venv import create


# import log
# import config parser
# import arg parse
# tpqm??


### Vars ###
install_options = ""
estimated_download_size = ""

# gather any command line args (if used) and put them into the variables used later in script
parser = argparse.ArgumentParser()
parser.add_argument("--instance_type", help="Is this Concierge instance for everyone (default) or standalone?")
parser.add_argument("--docker_volumes", help="Path where this Concierge instance will store data")
parser.add_argument("--compute_method", help="Do you want to use CPU or GPU acceleration?")
parser.add_argument("--language_model", help="What language model will this Concierge instance use?")
parser.add_argument("--activity_logging", help="Will this Concierge instance log activity? Strongly suggest setting this!")
parser.add_argument("--logging_directory", help="Path for logs to be written")
parser.add_argument("--log_retention", help="How long will logs be kept?")
args = parser.parse_args()

if args.instance_type:
    instance_type = args.instance_type
else:
    instance_type = ""

if args.docker_volumes:
    docker_volumes = args.docker_volumes
else:
    docker_volumes = ""

if args.compute_method:
    compute_method = args.compute_method
else:
    compute_method = ""

if args.language_model:
    language_model = args.language_model
else:
    language_model = ""

if args.activity_logging:
    activity_logging = args.activity_logging
else:
    activity_logging = ""

if args.logging_directory:
    logging_directory = args.logging_directory
else:
    logging_directory = ""

if args.log_retention:
    log_retention = args.log_retention
else:
    log_retention = ""

### functions ###
def pip_loader():
    working_dir = os.getcwd()
    print(working_dir)
    create(working_dir, with_pip=True)
    # pip install command
    run(["bin/pip", "install", "-r", abspath("requirements.txt")], cwd=working_dir)


def ollama_model_loader(model):
    print("foo")
    #docker exec -it ollama ollama run "MODEL HERE"


def validate_true_false_input(user_input):
    if user_input == True or user_input == False:
        #TODO do we need a log validation is ok?
        print("foo")
    else:
        print("for this question, you must answer True or False")
        # bug user again


def validate_path(user_input):
    print("foo")
    # check if path requested exists
    os.path.isdir()
    # if it doesn't do we have perms to create?
    # if not, let user know they'll be prompted for elevation during install


def check_libraries():
    #TODO make this useful (checking download size and post install preflight checks)
    print("foo")


def check_docker_image():
    print("foo")


def check_venv():
    if sys.prefix != sys.base_prefix:
        print("running in a venv. yay!")
    else:
        print("Concierge works best in a venv")


def docker_compose_helper(compute_method):
    if compute_method == "GPU":
        returncode = subprocess.call["/usr/bin/docker", "compose", "-f", abspath("docker-compose-gpu.yml"), "up", "-d"]
    else:
        returncode = subprocess.call["/usr/bin/docker", "compose", "up", "-d"]


### main ###
# determine os - needed for pathing and other OS specific options
platform = os.name

if platform == "posix":
    if os.geteuid() == 0:
        print("Please do not run this script as root or with sudo.")
        print("If needed, this script will prompt for elevated permission.")
        exit()

# TODO get info on how Windows answers this question
# if windows
#    please do not run this as the Administrator
# TODO get mac answers to this question
# if mac

# message:
print("\n\n\nConcierge: AI should be simple, safe, and amazing.\n\n\n")

# TODO check for existing Concierge instance
# if no concierge, do install
print("Welcome to the Concierge installer.")
print("Just a few configuration questions and then some download scripts will run.")
print("Note: you can just hit enter to accept the default option.\n\n")

# if prior concierge discovered, ask how to proceed
# list the docker containers and ask which ones they want to delete
# list the docker images and ask which ones they want to delete
# read the .env and ask if they want to delete the volumes


### meta info needed ###
print("\nQuestion 1 of X:")
if instance_type == "":
    print("Do you want this Concierge instance to be available for everyone on this system or just you?")
    print("Please choose 'everyone' (this is the default) or 'standalone' (just you):")
    # default to everyone
    instance_type = input("[everyone] or standalone: ").strip() or "everyone"
else:
    print("Answer provided by command line argument.")
install_options = install_options + " --instance_type="+instance_type

### docker ###
# set default docker volumes directory
if platform == "posix":
    #linux stand alone: ~/concierge/volumes
    if instance_type == "standalone":
        default_docker_directory = "~/concierge/volumes"
    #linux mulit user: /opt/concierge/volumes
    else:
        default_docker_directory = "/opt/concierge/volumes"
#   TODO windows standalone?
#   TODO windows everyone?
#   TODO mac standalone?
#   TODO mac everyone?

print("\nQuestion 2 of X:")
if docker_volumes == "":
    print("Where do you want your Concierge data to perist?")
    docker_volumes = input("path for data?[" + default_docker_directory +"]").strip() or default_docker_directory
else:
    print("Answer provided by command line argument.")
install_options = install_options + " --docker_volumes=" + docker_volumes

print("\nQusetion Y of X:")
if compute_method == "":
    print("Do you want to use CPU (default) or GPU compute to speed up Concierge responses?")
    compute_method = input("CPU or GPU?").strip() or "CPU"
else:
    print("Answer provided by command line argument.")
install_options = install_options + " --compute_method=" + compute_method

print("\nQuestion 3 of X:")
if language_model == "":
    print("Which language model do you want to use? ")
    print("note: the current recommended default for Concierge is mistral.")
    print("For more info on language models available please go here:")
    print("https://ollama.com/library")
    language_model = input("which language model? [mistral]").strip() or "mistral"
else:
    print("Answer provided by command line argument.")
install_options = install_options + " --language_model=" + language_model

# does path exist?
# if not, check perms... can create?
#     if not warn user will be asked for sudo/runas
# ask seb about local file path for loader... seems unneeded
# attempt to detect GPU
# if gpu present, prepare gpu compose
# if no gpu detected, mention CPU only will work, but it might be slightly slower
# docker compose
# check for presence of milvus images
# check for presence of ollama docker image
# catch to see if docker compose doesn't work
# if fails, see if you can use sudo


### logging ###
print("\nQuestion 4 of X:")
if activity_logging == "":
    print("Logging is a key component of Concierge")
    print("We strongly recommend you leave this enabled.")
    print("Your logs will remain local to your Concierge instance.")
    activity_logging = input("logging enabled? [True] or False").strip() or "True"
else:
    print("Answer provided by command line argument.")
install_options = install_options + " --activity_logging=" + activity_logging

print("\nQuestion 5 of X:")
# can skip if logging if disabled
if activity_logging == "False":
    print("skipping question, logging is disabled.")
else:
    if platform == "posix":
        if instance_type == "standalone":
            default_log_dir = "~/concierge/logs"
        else:
            default_log_dir = "/opt/concierge/logs"
    # TODO Windows
    # TODO Mac

    if logging_directory == "":
        print("Where would you like to store the Concierge logs?")
        logging_directory = input("log directory location: [" + default_log_dir + "]").strip() or default_log_dir
    else:
        print("Answer provided by command line argument.")
    install_options = install_options + " --logging_directory=" + logging_directory

print("\nQuestion 6 of X:")
if activity_logging == "False":
    print("skipping question, logging is disabled.")
else:
    if log_retention == "":
        print("How long do you want to keep Concierge activity logs?")
        log_retention = input("log retention length? Default is 90 days.").strip() or "90"
    else:
        print("Answer provided by command line argument.")
    install_options = install_options + " --log_retention=" + log_retention

# TODO future feature, help setup log export
# log export method?


### TODO RBAC ###


print("Concierge setup is almost complete.\n")
print("If you want to speed up the deployment of future Concierge instances with these exact options, save the command below.\n")
print("After git clone or unzipping, run this command and you can skip all these questions!\n\n")
print("\ninstall.py" + install_options + "\n\n\n")

print("About to make changes to your system.\n")
# TODO make a download size variable & update based on findings
print("Based on your selections, you will be downloading aproximately X of data")
print("Depending on network speed, this may take a while")
print("No changes have yet been made to your system. If you stop now or answer no, nothing will have changed.")
ready_to_rock = input("Ready to apply settings and start downloading? [Y/n]: ")

if ready_to_rock == "Y":
    # no further input is needed. Let's get to work.
    print("installing")

    # setup .env (needed for docker compose files)
    env_file = open(".env", "w")
    # write .env info needed
    env_file.write("DOCKER_VOLUME_DIRECTORY=" + docker_volumes)
    env_file.close()

    pip_loader()

    if compute_method == "GPU":
        docker_compose_helper("GPU")
    elif compute_method == "CPU":
        docker_compose_helper("CPU")
    else:
        #need to do input check to prevent this condition (and others like it)
        print("You have selected an unknown/unexpected compute method.")
        print("you will need to run the docker compose file manually")
        exit()
else:
    print("Install cancelled. No changes were made. Have a nice day! :-)\n\n")
    exit()

### do stuff ###

# write .env
# create docker volumes directory
# if fails, sudo or runas

# create venv
# pip command
# docker compose
# if fails, sudo or runas
# ollama model load
# verify everything is all good
	# do check to milvus api
	# check ollama api
	# check ollama mistral

print("Concierge is ready for use. Have a nice day! :-)\n\n")
# launch streamlit
