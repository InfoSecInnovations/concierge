import subprocess
import os
import shutil
from importlib.resources import files
from concierge_scripts.load_dotenv import load_env

cwd = os.path.abspath(os.path.join(files(), "..", "concierge_configurator"))


def destroy_instance():
    # note: we don't destroy Ollama because it takes a really long time to pull the models again and the settings are the same for all configurations.
    subprocess.run([shutil.which("bun"), "run", "./uninstallCli.ts"], cwd=cwd)


def create_instance(enable_security, launch_local):
    print("create instance")
    load_env()
    args = ["--host", "localhost", "--port", "15130"]
    if os.getenv("OLLAMA_SERVICE", "ollama").endswith("gpu"):
        args.append("--use-gpu")
    args.append("--dev-mode")
    if enable_security:
        args.append("--security-level")
        args.append("demo")
        args.append("--keycloak-password")
        args.append("ThisIsJustATest151")
    subprocess.run([shutil.which("bun"), "run", "./installCli.ts", *args], cwd=cwd)
    if launch_local:
        print("launch local")
        load_env()
        subprocess.run([shutil.which("bun"), "run", "./launchLocal.ts"], cwd=cwd)
