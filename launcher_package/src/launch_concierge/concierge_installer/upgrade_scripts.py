import shutil
import os
import subprocess


def remove_uploads(concierge_root_dir):
    uploads_dir = os.path.join(concierge_root_dir, "volumes", "file_uploads")
    if os.path.exists(uploads_dir):
        shutil.rmtree(uploads_dir)


def remove_opensearch(concierge_root_dir):
    subprocess.run(
        [
            "docker",
            "container",
            "rm",
            "--force",
            "opensearch-node1",
            "opensearch-dashboards",
        ],
        stdout=subprocess.DEVNULL,
    )
    opensearch_dir = os.path.join(concierge_root_dir, "volumes", "opensearch-data1")
    if os.path.exists(opensearch_dir):
        shutil.rmtree(opensearch_dir)


def upgrade040(concierge_root_dir):
    remove_uploads(concierge_root_dir)
    remove_opensearch(concierge_root_dir)


scripts = [{"version": "0.4.0", "func": upgrade040}]
