import os


def get_api_url():
    return (
        f"http://{os.getenv('API_HOST', 'localhost')}:{os.getenv('API_PORT', '15131')}"
    )
