import subprocess
import os
import shutil
import launch_concierge
import yaml
from script_builder.util import require_admin, get_lines, prompt_install
from script_builder.argument_processor import ArgumentProcessor
from importlib.metadata import version
from launch_concierge.concierge_installer.upgrade_scripts import scripts
from isi_util.list_util import find_index
from packaging.version import Version
from importlib.resources import files

package_dir = files(launch_concierge)


def init_arguments(install_arguments):
    require_admin()
    argument_processor = ArgumentProcessor(install_arguments)
    argument_processor.init_args()
    print("\n\n\nConcierge: AI should be simple, safe, and amazing.\n\n\n")
    return argument_processor


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
        concierge_root = ""
        existing_version = ""
        # read .env file manually because we don't necessarily have the pip requirements installed yet
        with open(".env") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("DOCKER_VOLUME_DIRECTORY="):
                    concierge_root = stripped.replace("DOCKER_VOLUME_DIRECTORY=", "")
                if stripped.startswith("CONCIERGE_VERSION="):
                    existing_version = stripped.replace("CONCIERGE_VERSION=", "")

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
                print(
                    "Detected older version of Concierge using volume mapping, we no longer support this configuration."
                )
                print(
                    "Removing the Concierge volumes will delete all ingested data and any language models you downloaded."
                )
                print(
                    "Apologies for the inconvenience, you will have to redownload the language models and recreate your collections."
                )
                print("This type of issue is to be expected during our alpha phase!")
                print("Remove Concierge volumes?")
                approve_to_delete = input(
                    f"Type 'yes' to delete {concierge_volumes} or press enter to skip: "
                )
                print("\n")
                if approve_to_delete == "yes":
                    shutil.rmtree(concierge_volumes)

            def check_dependencies(check_command, label, remove_command):
                result = get_lines(check_command)
                if result:
                    print(f"The following docker {label} were discovered:")
                    print(" ".join(result))

                    print("\nWould you like to have the installer remove any for you?")
                    to_remove = input(
                        f"Please give a space separated list of the {label} you would like removed or press enter to skip: "
                    )
                    print("\n")

                    if to_remove != "":
                        subprocess.run(
                            [*remove_command, *(" ".split(to_remove))],
                            stdout=subprocess.DEVNULL,
                        )
                else:
                    print(f"No existing docker {label} were found.\n")

            # docker containers
            check_dependencies(
                ["docker", "container", "ls", "--all", "--format", "{{.Names}}"],
                "containers",
                ["docker", "container", "rm", "--force"],
            )
            # docker networks
            check_dependencies(
                ["docker", "network", "ls", "--format", "{{.Name}}"],
                "networks",
                ["docker", "network", "rm"],
            )


def prompt_for_parameters(argument_processor):
    print("Welcome to the Concierge installer.")
    print("Just a few configuration questions and then some download scripts will run.")
    print("Note: you can just hit enter to accept the default option.\n\n")

    argument_processor.prompt_for_parameters()

    print("Concierge setup is almost complete.\n")
    print(
        "If you want to speed up the deployment of future Concierge instances with these exact options, save the command below.\n"
    )
    print(
        "After git clone or unzipping, run this command and you can skip all these questions!\n\n"
    )
    print(
        "\npython install.py" + argument_processor.get_command_parameters() + "\n\n\n"
    )

    print("About to make changes to your system.\n")
    # TODO make a download size variable & update based on findings
    # print("Based on your selections, you will be downloading aproximately X of data")
    # print("Depending on network speed, this may take a while")
    print(
        'No changes have yet been made to your system. If you stop now or answer "no", nothing will have changed.'
    )


def docker_compose_helper(environment, is_local=False, rebuild=False):
    filename = "docker-compose"
    if environment == "development":
        filename = f"{filename}-dev"
    if is_local:
        filename = f"{filename}-local"
    full_path = os.path.abspath(os.path.join(os.getcwd(), f"{filename}.yml"))
    if rebuild:
        # pull latest versions
        subprocess.run(["docker", "compose", "-f", full_path, "pull"])
        # build local concierge image
        subprocess.run(["docker", "compose", "-f", full_path, "build"])
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            full_path,
            "up",
            "-d",
        ]
    )


def prompt_concierge_install():
    prompt_install(
        "Ready to apply settings and start downloading?",
        "Install cancelled. No changes were made. Have a nice day! :-)",
    )


def do_install(argument_processor, environment="production", is_local=False):
    # the development environment uses different docker compose files which should already be in the cwd
    if environment != "development":
        # for production we need to copy the compose files from the package into the cwd because docker compose reads the .env file from the same directory as the launched files
        shutil.copytree(
            os.path.join(package_dir, "docker_compose"), os.getcwd(), dirs_exist_ok=True
        )
    with open("concierge.yml", "r") as file:  # TODO: write this file from user input
        config = yaml.safe_load(file)
    # setup .env (needed for docker compose files)
    env_lines = [
        "ENVIRONMENT=" + environment,
        "WEB_PORT=" + argument_processor.parameters["port"],
        "CONCIERGE_VERSION=" + version("launch_concierge"),
        "OLLAMA_SERVICE="
        + (
            "ollama-gpu"
            if argument_processor.parameters["compute_method"] == "GPU"
            else "ollama"
        ),
        "OPENSEARCH_SERVICE="
        + (
            "opensearch-node-enable-security"
            if "auth" in config
            else "opensearch-node-disable-security"
        ),
        "OPENSEARCH_DASHBOARDS_SERVICE="
        + (
            "opensearch-dashboards-base"
            if "auth" in config
            else "opensearch-dashboards-disable-security"
        ),
    ]
    # configure auth settings if needed
    if "auth" in config:
        open_id_config_path = os.path.abspath(
            os.path.join(
                os.getcwd(),
                "docker_compose_dependencies",
                "opensearch_config",
                "security_config_openid.yml",
            )
        )
        env_lines.extend(
            [
                "OPENSEARCH_CONFIG="
                + "./opensearch_config/opensearch_with_security.yml",
                "OPENSEARCH_SECURITY_CONFIG=" + open_id_config_path,
                "OPENSEARCH_ROLES_MAPPING=" + "./opensearch_config/roles_mapping.yml",
                "OPENSEARCH_INTERNAL_USERS=" + "./opensearch_config/internal_users.yml",
            ]
        )
        with open(
            os.path.join(
                package_dir,
                "docker_compose",
                "docker_compose_dependencies",
                "opensearch_config",
                "security_config_openid.yml",
            ),
            "r",
        ) as file:  # TODO: write this file from user input
            security_config = yaml.safe_load(file)
        auth = config["auth"]
        if "openid" in auth:
            for k, v in auth["openid"].items():
                # TODO: get order
                security_config["config"]["dynamic"]["authc"][f"openid_{k}"] = {
                    "http_enabled": True,
                    "transport_enabled": True,
                    "order": 0,
                    "http_authenticator": {
                        "type": "openid",
                        "challenge": False,
                        "config": {"openid_connect_url": v["url"]},
                    },
                    "authentication_backend": {"type": "noop"},
                }
                if "roles_key" in v:
                    security_config["config"]["dynamic"]["authc"][f"openid_{k}"][
                        "http_authenticator"
                    ]["config"]["roles_key"] = v["roles_key"]
        os.makedirs(os.path.dirname(open_id_config_path), exist_ok=True)
        with open(open_id_config_path, "w") as file:
            yaml.dump(security_config, file)
    with open(".env", "w") as env_file:
        # write .env info needed
        env_file.writelines("\n".join(env_lines))
    # docker compose
    docker_compose_helper(environment, is_local, True)
    # ollama model load
    subprocess.run(
        [
            "docker",
            "exec",
            "-it",
            "ollama",
            "ollama",
            "pull",
            argument_processor.parameters["language_model"],
        ]
    )


def set_compute(method: str):
    # because we have limited dependencies for the launcher scripts we remove and recreate the relevant line in the env file

    try:
        with open(".env", "r") as file:
            lines = file.readlines()
    except Exception:
        lines = []

    lines = [line for line in lines if not line.startswith("OLLAMA_SERVICE=")]
    lines.append(
        f'OLLAMA_SERVICE={"ollama-gpu" if method.lower() == "gpu" else "ollama"}'
    )

    with open(".env", "w") as file:
        file.writelines("\n".join(lines))
