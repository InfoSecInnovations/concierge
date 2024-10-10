import subprocess
import os
import shutil
from script_builder.argument_processor import ArgumentProcessor
from script_builder.util import get_strong_password
from importlib.metadata import version
from dotenv import set_key
from .package_dir import package_dir
from .docker_compose_helper import docker_compose_helper
import requests


def do_install(
    argument_processor: ArgumentProcessor, environment="production", is_local=False
):
    # the development environment uses different docker compose files which should already be in the cwd
    if environment != "development":
        # for production we need to copy the compose files from the package into the cwd because docker compose reads the .env file from the same directory as the launched files
        shutil.copytree(
            os.path.join(package_dir, "docker_compose"), os.getcwd(), dirs_exist_ok=True
        )
    if argument_processor.parameters["enable_security"]:
        # TODO: if security is already enabled, we shouldn't set it up again, criteria? keycloak container exists?
        keycloak_password = get_strong_password(
            "Enter password for initial Keycloak admin account"
        )
        opensearch_password = get_strong_password(
            "Enter password for OpenSearch admin account"
        )
        set_key(".env", "KEYCLOAK_INITIAL_ADMIN_PASSWORD", keycloak_password)
        # TODO: we should pass in front end host and port and use environment variables in the JSON
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                os.path.join(os.getcwd(), "docker-compose-launch-keycloak.yml"),
                "up",
                "-d",
            ]
        )
        # TODO: wait for launch
        response = requests.post(
            "http://localhost:8080/realms/master/protocol/openid-connect/token",
            {
                "client_id": "admin-cli",
                "grant_type": "password",
                "username": "admin",
                "password": keycloak_password,
            },
            verify=False,
        )
        token = response.json()["access_token"]
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        # TODO: we should get the client ID from the realm JSON file to avoid errors
        response = requests.get(
            "http://localhost:8080/admin/realms/concierge/clients/7a3ec428-36f2-49c4-91b1-8288dc44acb0/client-secret",
            headers=headers,
        )
        keycloak_secret = response.json()["value"]
        # TODO: set keycloak secret env variable
        set_key(".env", "KEYCLOAK_CLIENT_ID", "concierge-auth")
        set_key(".env", "KEYCLOAK_CLIENT_SECRET", keycloak_secret)
        set_key(".env", "OPENSEARCH_INITIAL_ADMIN_PASSWORD", opensearch_password)
        set_key(".env", "OPENSEARCH_SERVICE", "opensearch-node-enable-security")
        set_key(
            ".env",
            "OPENSEARCH_DASHBOARDS_SERVICE",
            "opensearch-dashboards-enable-security",
        )
        set_key(".env", "KEYCLOAK_SERVICE_FILE", "docker-compose-keycloak.yml")
    else:
        set_key(".env", "OPENSEARCH_SERVICE", "opensearch-node-disable-security")
        set_key(
            ".env",
            "OPENSEARCH_DASHBOARDS_SERVICE",
            "opensearch-dashboards-disable-security",
        )
        set_key(".env", "KEYCLOAK_SERVICE_FILE", "docker-compose-blank.yml")
    set_key(".env", "ENVIRONMENT", environment)
    set_key(".env", "WEB_PORT", str(argument_processor.parameters["port"]))
    set_key(".env", "CONCIERGE_VERSION", version("launch_concierge"))
    set_key(
        ".env",
        "OLLAMA_SERVICE",
        "ollama-gpu"
        if argument_processor.parameters["compute_method"].lower() == "gpu"
        else "ollama",
    )
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
