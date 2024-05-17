# this makes the parent directory be detected in Linux
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import subprocess
from script_builder.util import get_venv_executable
from concierge_backend_lib.status import check_ollama, check_opensearch
from concierge_installer.functions import docker_compose_helper

print("Checking Docker container status...\n")
requirements_met = False
if check_ollama():
    print("Ollama running")
    if check_opensearch():
        print("OpenSearch running")
        requirements_met = True
    else:
        print("OpenSearch not found")
else:
    print("Ollama not found")


if not requirements_met:
    print("Docker container dependencies don't appear to be running properly.")
    compute_method = input("Start docker containers with CPU or GPU? [CPU] or GPU:") or "CPU"
    if compute_method == 'GPU':
        docker_compose_helper('GPU')
    else:
        docker_compose_helper('CPU')


subprocess.run([get_venv_executable(), '-m', 'shiny', 'run', '--launch-browser', 'concierge_shiny/app.py'])
