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


def keycloak_exists():
    return container_exists("keycloak") and container_exists("postgres")
