import subprocess
import json


def container_exists(container_name):
    try:
        result = subprocess.run(
            ["docker", "inspect", "--type=container", container_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        parsed = json.loads(result.stdout)
        try:
            # ensure the container was created by the concierge docker compose
            return (
                parsed[0]["Config"]["Labels"]["com.docker.compose.project"]
                == "concierge"
            )
        except KeyError:
            return False
    except subprocess.CalledProcessError:
        return False


def remove_container(container_name):
    subprocess.run(["docker", "container", "rm", "--force", container_name])


def remove_volume(volume_name):
    subprocess.run(["docker", "volume", "rm", "--force", f"concierge_{volume_name}"])


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
