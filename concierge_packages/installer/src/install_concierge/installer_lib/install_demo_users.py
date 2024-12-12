import subprocess


def install_demo_users():
    subprocess.run(
        [
            "docker",
            "exec",
            "-d",
            "concierge",
            "python",
            "-m",
            "concierge_scripts.add_keycloak_demo_users",
        ]
    )
