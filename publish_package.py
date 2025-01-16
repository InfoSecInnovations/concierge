import os
import argparse
import subprocess
import shutil
from script_builder.util import get_venv_executable

parser = argparse.ArgumentParser()

parser.add_argument("package_name")
args = parser.parse_args()
package_name = args.package_name
cwd = os.getcwd()
package_dir = os.path.join(cwd, "concierge_packages", package_name)
os.chdir(package_dir)
shutil.rmtree("dist", ignore_errors=True)
subprocess.run(["python", "-m", "build"])
os.chdir(cwd)
subprocess.run(
    [
        get_venv_executable(),
        "-m",
        "twine",
        "upload",
        f"{os.path.join(package_dir, 'dist')}/*",
    ]
)
