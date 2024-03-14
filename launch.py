import subprocess
import os
from script_builder.util import get_venv_dir
from concierge_backend_lib.status import get_status
from concierge_installer.functions import docker_compose_helper

print("Checking Docker container status...\n")
status = get_status()

if not status["ollama"] or not status["milvus"]:
    print("Docker container dependencies don't appear to be running properly.")
    compute_method = input("Start docker containers with CPU or GPU? [CPU] or GPU:") or "CPU"
    if compute_method == 'GPU':
        docker_compose_helper('GPU')
    else:
        docker_compose_helper('CPU')

subprocess.run([os.path.join(get_venv_dir(), 'streamlit'), 'run', 'Concierge.py'])