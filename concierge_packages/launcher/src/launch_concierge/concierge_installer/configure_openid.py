import yaml
from script_builder.util import (
    get_valid_input,
)
from getpass import getpass
from dotenv import set_key
import re


def configure_openid():
    print(
        "To add an OpenID provider you will need to register an app to obtain a client ID and client secret."
    )
    print(
        "You will also need to locate the configuration URL that usually looks something like this: https://www.example.com/.well-known/openid-configuration"
    )
    print(
        "If possible, we recommend using a provider that supports assigning roles using OpenID claims. This is simpler than having to assign permissions within Concierge."
    )
    try:
        with open("concierge.yml", "r") as file:
            config = yaml.safe_load(file)
    except Exception:
        config = {}
    existing = []
    if "auth" in config and "openid" in config["auth"]:
        existing = config["auth"]["openid"].keys()
        if len(existing):
            print(f"Providers already configured: {', '.join(existing)}")
    label_prompt = "Assign a name to this provider, if it matches an existing one the old config will be overwritten."
    # if a config exists the user can just keep that, if not they must enter a valid one
    if existing:
        print(label_prompt)
        label = input("Leave this blank to keep existing configuration: ").strip()
        if not label:
            return
    else:
        label = get_valid_input(f"{label_prompt}: ")
    config_url = get_valid_input(
        "Please enter your OpenID provider's configuration URL: "
    )
    client_id = get_valid_input("Please enter your app's client ID: ")
    client_secret = getpass("Please enter your app's client secret: ")
    print("Which OpenID claim is used to assign user roles?")
    roles_key = input(
        'It\'s commonly "roles" but this can vary depending on your provider. Leave blank if not applicable: '
    ).strip()
    label_stripped = re.sub(r"\W+", "", label.lower())
    id_key = f"{label_stripped.upper()}_CLIENT_ID"
    secret_key = f"{label_stripped.upper()}_CLIENT_SECRET"
    if "auth" not in config:
        config["auth"] = {}
    if "openid" not in config["auth"]:
        config["auth"]["openid"] = {}
    config["auth"]["openid"][label_stripped] = {
        "url": config_url,
        "id_env_var": id_key,
        "secret_env_var": secret_key,
        "display_name": label,
    }
    if roles_key:
        config["auth"]["openid"][label_stripped]["roles_key"] = roles_key
    with open("concierge.yml", "w") as file:
        file.write(yaml.dump(config))
    set_key(".env", id_key, client_id)
    set_key(".env", secret_key, client_secret)
