import json
from importlib.resources import files
import os
from shabti_keycloak import get_keycloak_admin_client


def add_users():
    print("\nAdding demo Keycloak users...")
    with open(os.path.join(files(), "keycloak_users", "users.json"), "r") as file:
        users_data = json.load(file)
    client = get_keycloak_admin_client()
    for user in users_data:
        user_id = client.create_user(user)
        # creating with roles unfortunately doesn't work even though it's implied in the documentation1
        # so we have to add the mapping separately
        if "clientRoles" in user:
            for client_name, roles in user["clientRoles"].items():
                client_id = client.get_client_id(client_name)
                client.assign_client_role(
                    user_id,
                    client_id,
                    [client.get_client_role(client_id, role) for role in roles],
                )
        print(f"Added user {user['username']}")


if __name__ == "__main__":
    add_users()
