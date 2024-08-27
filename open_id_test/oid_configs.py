import requests
import yaml

with open("concierge.yml", "r") as file:
    config = yaml.safe_load(file)
    if "auth" in config and "openid" in config["auth"]:
        oauth_config_data = config["auth"]["openid"]

oauth_configs = {
    provider: requests.get(data["url"]).json()
    for provider, data in oauth_config_data.items()
}
