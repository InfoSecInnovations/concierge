import subprocess
import sys
from script_builder_package.src.script_builder.util import (
    get_venv_executable,
    setup_pip,
    install_requirements,
    require_admin,
)

require_admin()
setup_pip()
install_requirements("dev_requirements.txt")

subprocess.run([get_venv_executable(), "dev_installer.py", *sys.argv[1:]])
