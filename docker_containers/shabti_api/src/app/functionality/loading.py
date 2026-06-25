from typing import BinaryIO

from .loaders.base_loader import ShabtiDocument
from .loaders.tika_loader import TikaFileLoader


def load_file(file: BinaryIO, filename) -> ShabtiDocument | None:
    file.seek(0)
    return TikaFileLoader.load(file, filename)
