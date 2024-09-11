import subprocess
from concierge_packages.script_builder.src.script_builder.util import (
    get_venv_executable,
)

subprocess.run(
    [get_venv_executable(), "dev_launcher.py", "--environment", "development"]
)
