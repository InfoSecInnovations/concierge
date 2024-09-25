import subprocess
import os
import shutil
import yaml
from script_builder.argument_processor import ArgumentProcessor
from importlib.metadata import version
from dotenv import load_dotenv, set_key
from .configure_openid import configure_openid
from .package_dir import package_dir
from .docker_compose_helper import docker_compose_helper


def do_install(
    argument_processor: ArgumentProcessor, environment="production", is_local=False
):
    # delete existing auth if requested, we must do this before configuring OpenID so these actions don't step on each other
    if (
        "delete_auth" in argument_processor.parameters
        and argument_processor.parameters["delete_auth"]
    ):
        try:
            with open("concierge.yml", "r") as file:
                config = yaml.safe_load(file)
                del config["auth"]
            with open("concierge.yml", "w") as file:
                file.write(yaml.dump(config))
        except Exception:
            pass
    # the development environment uses different docker compose files which should already be in the cwd
    if environment != "development":
        # for production we need to copy the compose files from the package into the cwd because docker compose reads the .env file from the same directory as the launched files
        shutil.copytree(
            os.path.join(package_dir, "docker_compose"), os.getcwd(), dirs_exist_ok=True
        )
    if (
        "enable_openid" in argument_processor.parameters
        and argument_processor.parameters["enable_openid"]
    ):
        configure_openid()
    try:
        with open("concierge.yml", "r") as file:
            config = yaml.safe_load(file)
    except Exception:
        config = {}
    auth_configured = False
    load_dotenv(".env")  # load env after setting OpenID so the variables are up to date
    # configure auth settings if needed
    if "auth" in config:
        print("Authentication configuration detected.")
        open_id_config_path = os.path.abspath(
            os.path.join(
                os.getcwd(),
                "docker_compose_dependencies",
                "opensearch_config",
                "security_config_openid.yml",
            )
        )
        dashboards_open_id_config_path = os.path.abspath(
            os.path.join(
                os.getcwd(),
                "docker_compose_dependencies",
                "opensearch_config",
                "opensearch_dashboards_openid.yml",
            )
        )
        cert_dir = os.path.join(
            package_dir, "docker_compose", "docker_compose_dependencies", "certificates"
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
        ) as file:
            security_config = yaml.safe_load(file)
        with open(
            os.path.join(
                package_dir,
                "docker_compose",
                "docker_compose_dependencies",
                "opensearch_config",
                "opensearch_dashboards_openid.yml",
            ),
            "r",
        ) as file:
            dashboards_config = yaml.safe_load(file)
        auth = config["auth"]
        if "openid" in auth:
            for k, v in auth["openid"].items():
                client_id = os.getenv(v["id_env_var"])
                if not client_id:
                    print(
                        f"No client ID was found for OpenID provider {k}, this provider will be skipped!"
                    )
                    continue
                client_secret = os.getenv(v["secret_env_var"])
                if not client_secret:
                    print(
                        f"No client secret was found for OpenID provider {k}, this provider will be skipped!"
                    )
                    continue
                set_key(".env", v["id_env_var"], client_id)
                set_key(".env", v["secret_env_var"], client_secret)

                order = 0

                def order_available():
                    for conf in security_config["config"]["dynamic"]["authc"].values():
                        if conf["order"] == order:
                            return False
                    return True

                while not order_available():
                    order += 1
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
                dashboards_config["opensearch_security.openid.connect_url"] = v["url"]
                dashboards_config["opensearch_security.openid.client_id"] = client_id
                dashboards_config["opensearch_security.openid.client_secret"] = (
                    client_secret
                )
                print(f"OpenID provider {k} was enabled.")
                auth_configured = True
            if not auth_configured:
                print(
                    "OpenID was configured in Concierge configuration file but client ID or secret are missing from the environment file."
                )
                print(
                    "Please rerun the installer and either remove authentication or make sure to input a valid OpenID client ID and secret."
                )
                exit()

        os.makedirs(os.path.dirname(open_id_config_path), exist_ok=True)
        with open(open_id_config_path, "w") as file:
            yaml.dump(security_config, file)
        os.makedirs(os.path.dirname(dashboards_open_id_config_path), exist_ok=True)
        with open(dashboards_open_id_config_path, "w") as file:
            yaml.dump(dashboards_config, file)
        set_key(
            ".env",
            "OPENSEARCH_CONFIG",
            "./opensearch_config/opensearch_with_security.yml",
        )
        set_key(".env", "OPENSEARCH_SECURITY_CONFIG", open_id_config_path)
        set_key(".env", "OPENSEARCH_DASHBOARDS_CONFIG", dashboards_open_id_config_path)
        set_key(
            ".env", "OPENSEARCH_ROLES_MAPPING", "./opensearch_config/roles_mapping.yml"
        )
        set_key(
            ".env",
            "OPENSEARCH_INTERNAL_USERS",
            "./opensearch_config/internal_users.yml",
        )
        set_key(
            ".env",
            "OPENSEARCH_DASHBOARDS_CERT",
            os.path.abspath(os.path.join(cert_dir, "esnode.pem")),
        )
        set_key(
            ".env",
            "OPENSEARCH_DASHBOARDS_KEY",
            os.path.abspath(os.path.join(cert_dir, "esnode-key.pem")),
        )
        set_key(
            ".env",
            "OPENSEARCH_DASHBOARDS_CA",
            os.path.abspath(os.path.join(cert_dir, "root-ca.pem")),
        )
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
    set_key(
        ".env",
        "OPENSEARCH_SERVICE",
        "opensearch-node-enable-security"
        if auth_configured
        else "opensearch-node-disable-security",
    )
    set_key(
        ".env",
        "OPENSEARCH_DASHBOARDS_SERVICE",
        "opensearch-dashboards-enable-security"
        if auth_configured
        else "opensearch-dashboards-disable-security",
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
