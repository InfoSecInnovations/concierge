import subprocess
import os


def docker_compose_helper(compute_method):
    if compute_method == "GPU":
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                os.path.abspath("docker-compose-gpu.yml"),
                "up",
                "-d",
            ]
        )
    else:
        subprocess.run(["docker", "compose", "up", "-d"])
