import subprocess
import json


def item_exists(item_name, item_type):
    try:
        result = subprocess.run(
            ["docker", "inspect", f"--type={item_type}", item_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        parsed = json.loads(result.stdout)
        try:
            # ensure the container was created by the concierge docker compose
            if parsed[0]["Labels"]["com.docker.compose.project"] == "concierge":
                return True

        except KeyError:
            try:
                return (
                    parsed[0]["Config"]["Labels"]["com.docker.compose.project"]
                    == "concierge"
                )
            except KeyError:
                return False
    except subprocess.CalledProcessError:
        return False


def container_exists(container_name):
    return item_exists(container_name, "container")


def volume_exists(volume_name):
    return item_exists(f"concierge_{volume_name}", "volume")


def remove_container(container_name):
    subprocess.run(
        ["docker", "container", "rm", "--force", container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def remove_volume(volume_name):
    subprocess.run(
        ["docker", "volume", "rm", "--force", f"concierge_{volume_name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def keycloak_exists():
    return container_exists("keycloak") and container_exists("postgres")


def remove_keycloak():
    remove_container("keycloak")
    remove_container("postgres")
    remove_volume("postgres_data")


def ollama_exists():
    return container_exists("ollama")


def remove_ollama():
    remove_container("ollama")
    remove_volume("ollama")


def opensearch_exists():
    return container_exists("opensearch-node1")


def remove_opensearch():
    remove_container("opensearch-node1")
    remove_container("opensearch-dashboards")
    remove_volume("opensearch-data1")
