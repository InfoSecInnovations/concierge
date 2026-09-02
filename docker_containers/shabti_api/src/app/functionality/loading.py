from typing import BinaryIO

from .loaders.base_loader import ShabtiPageStream
from .loaders.tika_loader import TikaFileLoader


def load_file(file: BinaryIO, filename) -> ShabtiPageStream:
    file.seek(0)
    return TikaFileLoader.load(file, filename)
