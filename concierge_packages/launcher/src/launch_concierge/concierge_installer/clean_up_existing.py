import subprocess
import os
import shutil
from importlib.metadata import version
from launch_concierge.concierge_installer.upgrade_scripts import scripts
from isi_util.list_util import find_index
from packaging.version import Version
from dotenv import load_dotenv
from .package_dir import package_dir
from .docker_containers import (
    opensearch_exists,
    keycloak_exists,
    ollama_exists,
    remove_opensearch,
    remove_keycloak,
    remove_ollama,
    volume_exists,
)


def clean_up_existing():
    # If Docker isn't present, there's no point in proceeding
    if not shutil.which("docker"):
        print(
            "Docker isn't installed. You will need it to be able to proceed, please install Docker or use a machine which has it installed!"
        )
        exit()

    # check if docker is running
    process_info = subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    # if it's not running we can't check anything docker related
    if process_info.returncode == 1:
        print("Docker isn't running.")
        print(
            "This script requires the Docker daemon to be running. Please start it and rerun the script once it's up and running."
        )
        exit()

    if os.path.exists(os.path.join(package_dir, "volumes")):
        print("/!\\ WARNING /!\\\n")
        print(f'"volumes" directory was found in {package_dir}')
        print(
            "This is probably the result of an issue caused by a previous version which was ignoring the user's settings and incorrectly creating the Concierge volumes inside the package install directory."
        )
        proceed = False
        while not proceed:
            prompt = input("Quit installer to move or remove directory? yes/no: ")
            if prompt.upper() == "YES":
                exit()
            if prompt.upper() == "NO":
                proceed = True
            else:
                print("Please enter yes or no!")

    # Check if Concierge is already configured
    if os.path.isfile(".env"):
        load_dotenv(".env", override=True)
        concierge_root = os.getenv("DOCKER_VOLUME_DIRECTORY")
        existing_version = os.getenv("CONCIERGE_VERSION")

        # if an existing version is found, we take that to mean it has previously been installed, we also check the directory to see if an older version using a mount was installed
        if concierge_root or existing_version:
            print("Concierge instance discovered.")
            print("This script can help reset your system for a re-install.\n")

            new_version = version("launch_concierge")
            if existing_version and new_version != existing_version:
                # find if we have any upgrade scripts between the existing and new version
                start_index = find_index(
                    scripts,
                    lambda s: (
                        not existing_version
                        or Version(s["version"]) > Version(existing_version)
                    )  # if there's no existing version we start from zero
                    and Version(s["version"]) <= Version(new_version),
                )
                if start_index >= 0:
                    print("Incompatible previous version detected.")
                    print(
                        "It is strongly recommended you let this installer run the upgrade scripts to remove outdated elements."
                    )
                    print(
                        "This may result in loss of data, e.g. your document collections."
                    )
                    print(
                        "We apologize for any inconvenience caused, this product is still in Alpha and the configuration is shifting a lot. As we approach the stable release, features will be added to mitigate data loss when upgrading."
                    )
                    proceed = input("Run upgrade scripts? [yes]/no: ") or "yes"
                    if proceed.upper() == "YES":
                        print(
                            "\nCleaning up incompatible elements from previous installations...\n"
                        )
                        # iterate until we reach a script with a higher version than the new one (although ideally the user is installing latest and this won't happen)
                        for s in scripts[start_index:]:
                            if Version(s["version"]) > Version(new_version):
                                break
                            s["func"](concierge_root)  # execute upgrade function
                        print("\nCleanup of previous incompatible elements complete.\n")
                        print("\nThe following cleanup steps are optional.\n")

            # option to remove volumes directory
            if concierge_root:
                concierge_volumes = os.path.join(concierge_root, "volumes")
                if os.path.exists(concierge_volumes):
                    print(
                        "Detected older version of Concierge using volume mapping, we no longer support this configuration."
                    )
                    print(
                        "Removing the Concierge volumes will delete all ingested data and any language models you downloaded."
                    )
                    print(
                        "Apologies for the inconvenience, you will have to redownload the language models and recreate your collections."
                    )
                    print(
                        "This type of issue is to be expected during our alpha phase!"
                    )
                    print("Remove Concierge volumes?")
                    approve_to_delete = input(
                        f"Type 'yes' to delete {concierge_volumes} or press enter to skip: "
                    )
                    print("\n")
                    if approve_to_delete == "yes":
                        shutil.rmtree(concierge_volumes)

            # we also check the volumes here because the user needs the opportunity to remove a dependency completely even if they already deleted the containers

            if opensearch_exists() or volume_exists("opensearch-data1"):
                print("\nExisting OpenSearch installation found")
                print("If you remove this you will lose all your document collections!")
                approve_to_delete = input(
                    "Type 'yes' to remove OpenSearch installation or press enter to skip: "
                )
                if approve_to_delete:
                    remove_opensearch()

            if ollama_exists() or volume_exists("ollama"):
                print("\nExisting Ollama installation found")
                print(
                    "If you remove this you will need to redownload the language model(s) used by the prompter"
                )
                approve_to_delete = input(
                    "Type 'yes' to remove Ollama installation or press enter to skip: "
                )
                if approve_to_delete:
                    remove_ollama()

            if keycloak_exists() or volume_exists("postgres_data"):
                print("\nExisting Keycloak installation found")
                print(
                    "If you remove this you will lose all configured users and access controls!"
                )
                approve_to_delete = input(
                    "Type 'yes' to remove Keycloak installation or press enter to skip: "
                )
                if approve_to_delete:
                    remove_keycloak()
