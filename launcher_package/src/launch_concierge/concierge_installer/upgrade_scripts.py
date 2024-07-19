import shutil
import os
import subprocess


def rm_volume(concierge_root_dir, volume_name):
    volume_dir = os.path.join(concierge_root_dir, "volumes", volume_name)
    if os.path.exists(volume_dir):
        print(f"Deleting {volume_name} data volume...")
        shutil.rmtree(volume_dir)


def remove_uploads(concierge_root_dir):
    rm_volume(concierge_root_dir, "file_uploads")


def remove_opensearch(concierge_root_dir):
    print("Removing existing OpenSearch installation if present...")
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
        stderr=subprocess.DEVNULL,  # this can error if some containers don't exist, so we just hide the errors
    )
    rm_volume(concierge_root_dir, "opensearch-data1")


def remove_milvus(concierge_root_dir):
    print("Removing existing Milvus installation if present...")
    subprocess.run(
        [
            "docker",
            "container",
            "rm",
            "--force",
            "milvus-etcd",
            "milvus-minio",
            "milvus-standalone",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,  # this can error if some containers don't exist, so we just hide the errors
    )
    rm_volume(concierge_root_dir, "milvus")
    rm_volume(concierge_root_dir, "etcd")
    rm_volume(concierge_root_dir, "minio")


def upgrade040(concierge_root_dir):
    remove_milvus(concierge_root_dir)
    remove_uploads(concierge_root_dir)
    remove_opensearch(concierge_root_dir)


scripts = [{"version": "0.4rc0", "func": upgrade040}]
