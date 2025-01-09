import subprocess
import os


def docker_compose_helper(environment, is_local=False, rebuild=False):
    filename = "docker-compose"
    if is_local:
        filename = f"{filename}-local"
    elif environment == "development":
        filename = f"{filename}-dev"
    full_path = os.path.abspath(os.path.join(os.getcwd(), f"{filename}.yml"))
    if rebuild:
        # pull latest versions
        subprocess.run(["docker", "compose", "-f", full_path, "pull"])
    if is_local:
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
