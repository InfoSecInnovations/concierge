from ..loaders.base_loader import ShabtiDocument
from ..loaders.tika_loader import TikaFileLoader


def load_file(file, filename) -> ShabtiDocument | None:
    return TikaFileLoader.load(file, filename)
