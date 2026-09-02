# TikaFileLoader.load is an HTTP call to the Tika service, so this is not a unit test and
# lives here rather than in tests/unit, which the runner's unit lane runs with no containers at all.
from ...src.app.functionality.loaders.tika_loader import TikaFileLoader
import os
from fastapi import UploadFile
from io import BytesIO

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


def test_tika_loader():
    with open(file_path, "rb") as f:
        doc = TikaFileLoader.load(f, filename)
        assert len(doc.pages)


def test_tika_loader_with_upload_file():
    with open(file_path, "rb") as f:
        uf = UploadFile(file=BytesIO(f.read()), filename=filename)
    with uf.file as f:
        doc = TikaFileLoader.load(uf.file, filename)
        assert len(doc.pages)
