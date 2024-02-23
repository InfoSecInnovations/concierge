import platform
import os
import ctypes

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

def get_default_directory(is_standalone: bool):
    if my_platform == "Linux":
        if is_standalone:
            return "~/"
        return "/opt/"
    if my_platform == "Windows":
        if is_standalone:
            return os.getenv('LOCALAPPDATA')
        return "C:\ProgramData"
    # TODO: macOS