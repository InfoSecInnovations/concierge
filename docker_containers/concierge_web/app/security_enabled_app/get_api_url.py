import os


def get_api_url():
    return (
        f"https://{os.getenv("API_HOST", "localhost")}:{os.getenv("API_PORT", "15131")}"
    )
