import platform
import os
import ctypes
import subprocess
import venv

my_platform = platform.system()

def disallow_admin():
    if my_platform == "Linux":
        if os.geteuid() == 0:
            print("Please do not run this script as root or with sudo.")
            print("If needed, this script will prompt for elevated permission.")
            exit()
    if my_platform == "Windows":
        if ctypes.windll.shell32.IsUserAnAdmin() != 0:
            print("Please do not run this script as administrator")
            print("If needed, this script will prompt for elevated permission.")
            exit()
    # TODO: macOS

def require_admin():
    if my_platform == "Linux":
        if os.geteuid() != 0:
            print("Please run this script as root or with sudo.")
            exit()
    if my_platform == "Windows":
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:
            print("Please run this script as administrator")
            exit()
    # TODO: macOS

def get_default_directory(is_standalone: bool):
    if my_platform == "Linux":
        if is_standalone:
            return "~/"
        return "/opt/"
    if my_platform == "Windows":
        if is_standalone:
            return os.getenv('LOCALAPPDATA')
        return r"C:\ProgramData"
    # TODO: macOS

def get_venv_executable():
    if my_platform == "Linux":
        path="bin"
    else:
        path="Scripts"
    # TODO: macOS
    return os.path.join(path, "python")

def pip_loader():
    working_dir = os.getcwd()
    venv.create(working_dir, with_pip=True)
    # pip install command
    subprocess.run([get_venv_executable(), "-m", "pip", "install", "-r", os.path.abspath("requirements.txt")], cwd=working_dir)