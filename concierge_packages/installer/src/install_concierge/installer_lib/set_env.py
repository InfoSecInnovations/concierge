from dotenv import set_key
import os


def set_env(key, value):
    set_key(".env", key, value)
    os.environ[key] = value
