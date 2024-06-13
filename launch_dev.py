import subprocess
from script_builder_package.src.script_builder.util import get_venv_executable

subprocess.run(
    [get_venv_executable(), "dev_launcher.py", "--environment", "development"]
)
