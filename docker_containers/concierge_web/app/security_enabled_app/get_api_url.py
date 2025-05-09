import os


def get_api_url():
    override_host = os.getenv("OVERRIDE_API_HOST")
    if override_host:
        return override_host
    return (
        f"https://{os.getenv('API_HOST', 'localhost')}:{os.getenv('API_PORT', '15131')}"
    )
