import json
from importlib.resources import files
import os
from concierge_backend_lib.authentication import get_keycloak_admin_client


def add_users():
    print("\nAdding demo Keycloak users...")
    with open(os.path.join(files(), "keycloak_users", "users.json"), "r") as file:
        users_data = json.load(file)
    client = get_keycloak_admin_client()
    for user in users_data:
        client.create_user(user)
        print(f"Added user {user["username"]}")


if __name__ == "__main__":
    add_users()
