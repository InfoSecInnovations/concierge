import platform
import os
import ctypes
import subprocess
import venv

my_platform = platform.system()
is_unix = my_platform == "Linux" or my_platform == "Darwin"


def disallow_admin():
    if is_unix:
        if os.geteuid() == 0:
            print("Please do not run this script as root or with sudo.")
            print("If needed, this script will prompt for elevated permission.")
            exit()
    if my_platform == "Windows":
        if ctypes.windll.shell32.IsUserAnAdmin() != 0:
            print("Please do not run this script as administrator")
            print("If needed, this script will prompt for elevated permission.")
            exit()


def require_admin():
    if is_unix:
        if os.geteuid() != 0:
            print("Please run this script as root or with sudo.")
            exit()
    if my_platform == "Windows":
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:
            print("Please run this script as administrator")
            exit()


def get_default_directory(is_standalone: bool):
    if is_unix:
        if is_standalone:
            return "~/"
        return "/opt/"
    if my_platform == "Windows":
        if is_standalone:
            return os.getenv("LOCALAPPDATA")
        return os.getenv("PROGRAMDATA")


def get_venv_path():
    if is_unix:
        return "bin"
    return "Scripts"


def get_venv_executable():
    return os.path.join(get_venv_path(), "python")


def install_requirements(filename="requirements.txt"):
    subprocess.run(
        [
            get_venv_executable(),
            "-m",
            "pip",
            "install",
            "-r",
            os.path.abspath(filename),
        ]
    )


def setup_pip():
    working_dir = os.getcwd()
    venv.create(working_dir, with_pip=True)
    install_requirements()


def get_lines(command):
    return list(
        filter(
            None,
            subprocess.run(command, capture_output=True, text=True).stdout.split("\n"),
        )
    )


def get_install_status(apply_message, cancel_message):
    ready_to_rock = input(
        f'{apply_message} Please type "yes" to continue. (yes/no): '
    ).upper()

    if ready_to_rock == "YES":
        # no further input is needed. Let's get to work.
        print("installing...")
        return True

    elif ready_to_rock == "NO":
        print(f"{cancel_message}\n\n")
        exit()

    else:
        return False


def prompt_install(apply_message, cancel_message):
    while not get_install_status(apply_message, cancel_message):
        print("Answer needs to be yes or no!\n")
