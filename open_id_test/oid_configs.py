import requests

oauth_config_data = {
    "google": {
        "url": "https://accounts.google.com/.well-known/openid-configuration",
        "id_env_var": "GOOGLE_CLIENT_ID",
        "secret_env_var": "GOOGLE_CLIENT_SECRET",
    },
    "microsoft": {
        "url": "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        "id_env_var": "MICROSOFT_CLIENT_ID",
        "secret_env_var": "MICROSOFT_CLIENT_SECRET",
    },
}

oauth_configs = {
    provider: requests.get(data["url"]).json()
    for provider, data in oauth_config_data.items()
}
