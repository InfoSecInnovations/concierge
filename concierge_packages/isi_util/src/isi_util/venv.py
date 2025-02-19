import os
import platform

my_platform = platform.system()
is_unix = my_platform == "Linux" or my_platform == "Darwin"


def get_venv_path():
    if is_unix:
        return "bin"
    return "Scripts"


def get_venv_executable():
    return os.path.join(get_venv_path(), "python")
