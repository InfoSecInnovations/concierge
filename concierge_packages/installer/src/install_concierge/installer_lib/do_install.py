import subprocess
import os
import shutil
from script_builder.argument_processor import ArgumentProcessor
from isi_util.password import get_strong_password, generate_strong_password
from importlib.metadata import version
from .package_dir import package_dir
from .docker_compose_helper import docker_compose_helper
import requests
from concierge_util import load_config, write_config
from .set_env import set_env
from .docker_containers import keycloak_exists
from .create_certificates import create_certificates


def do_install(
    argument_processor: ArgumentProcessor, environment="production", is_local=False
):
    # the development environment uses different docker compose files which should already be in the cwd
    if environment != "development":
        # for production we need to copy the compose files from the package into the cwd because docker compose reads the .env file from the same directory as the launched files
        shutil.copytree(
            os.path.join(package_dir, "docker_compose"), os.getcwd(), dirs_exist_ok=True
        )
    config = load_config()
    # Keycloak needs the host and port to be set before as these are piped into the initial realm config
    set_env("WEB_HOST", argument_processor.parameters["host"])
    set_env("WEB_PORT", str(argument_processor.parameters["port"]))
    if argument_processor.parameters["security_level"] != "None":
        set_env("CONCIERGE_SECURITY_ENABLED", "True")
        set_env("CONCIERGE_SERVICE", "concierge-enable-security")
        # TODO: handle existing certificates
        # TODO: handle certificates supplied by the user
        cert_dir = os.path.join(os.getcwd(), "self_signed_certificates")
        create_certificates(cert_dir)
        set_env("ROOT_CA", os.path.join(cert_dir, "root-ca.pem"))
        set_env(
            "OPENSEARCH_CLIENT_CERT",
            os.path.join(cert_dir, "opensearch-admin-client-cert.pem"),
        )
        set_env(
            "OPENSEARCH_CLIENT_KEY",
            os.path.join(cert_dir, "opensearch-admin-client-key.pem"),
        )
        set_env(
            "OPENSEARCH_ADMIN_KEY", os.path.join(cert_dir, "opensearch-admin-key.pem")
        )
        set_env(
            "OPENSEARCH_ADMIN_CERT", os.path.join(cert_dir, "opensearch-admin-cert.pem")
        )
        set_env(
            "OPENSEARCH_NODE_CERT", os.path.join(cert_dir, "opensearch-node1-cert.pem")
        )
        set_env(
            "OPENSEARCH_NODE_KEY", os.path.join(cert_dir, "opensearch-node1-key.pem")
        )
        set_env("KEYCLOAK_CERT", os.path.join(cert_dir, "keycloak-cert.pem"))
        set_env("KEYCLOAK_CERT_KEY", os.path.join(cert_dir, "keycloak-key.pem"))
        set_env("WEB_CERT", os.path.join(cert_dir, "concierge-cert.pem"))
        set_env("WEB_KEY", os.path.join(cert_dir, "concierge-key.pem"))
        # we only configure Keycloak if it wasn't already present
        if not keycloak_exists():
            keycloak_password = get_strong_password(
                "Enter password for initial Keycloak admin account: "
            )
            db_password = generate_strong_password()
            set_env("KEYCLOAK_INITIAL_ADMIN_PASSWORD", keycloak_password)
            set_env("POSTGRES_DB_PASSWORD", db_password)
            full_path = os.path.join(os.getcwd(), "docker-compose-launch-keycloak.yml")
            # pull latest versions before launching Keycloak, otherwise the instance gets broken if new images are pulled during the next step
            subprocess.run(["docker", "compose", "-f", full_path, "pull"])
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
            # TODO: some kind of timeout on this?
            print(
                "Waiting for Keycloak to start so we can get the OpenID credentials..."
            )
            print("This can take a few minutes, please be patient!")
            while True:
                try:
                    response = requests.post(
                        "https://localhost:8443/realms/master/protocol/openid-connect/token",
                        {
                            "client_id": "admin-cli",
                            "grant_type": "password",
                            "username": "admin",
                            "password": keycloak_password,
                        },
                        verify=os.getenv("ROOT_CA"),
                    )
                    token = response.json()["access_token"]
                    headers = {
                        "content-type": "application/json",
                        "Authorization": f"Bearer {token}",
                    }
                    # TODO: we should get the client ID from the realm JSON file to avoid errors
                    response = requests.get(
                        "https://localhost:8443/admin/realms/concierge/clients/7a3ec428-36f2-49c4-91b1-8288dc44acb0/client-secret",
                        headers=headers,
                        verify=os.getenv("ROOT_CA"),
                    )
                    keycloak_secret = response.json()["value"]
                    break
                except Exception:
                    pass

            set_env("KEYCLOAK_CLIENT_ID", "concierge-auth")
            set_env("KEYCLOAK_CLIENT_SECRET", keycloak_secret)
        set_env("OPENSEARCH_SERVICE", "opensearch-node-enable-security")

        set_env("KEYCLOAK_SERVICE_FILE", "docker-compose-keycloak.yml")
    else:
        set_env("CONCIERGE_SERVICE", "concierge")
        set_env("CONCIERGE_SECURITY_ENABLED", "False")
        set_env("OPENSEARCH_SERVICE", "opensearch-node-disable-security")
        set_env("KEYCLOAK_SERVICE_FILE", "docker-compose-blank.yml")
    set_env("ENVIRONMENT", environment)
    set_env("CONCIERGE_VERSION", version("install_concierge"))
    set_env(
        "OLLAMA_SERVICE",
        "ollama-gpu"
        if argument_processor.parameters["compute_method"].lower() == "gpu"
        else "ollama",
    )
    write_config(config)
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
