import subprocess
from script_builder.util import get_venv_executable

subprocess.run([get_venv_executable(), "dev_launcher.py"])
