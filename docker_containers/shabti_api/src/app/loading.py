from ..loaders.base_loader import ShabtiDocument
from ..loaders.unstructured import UnstructuredFileLoader


def load_file(file, filename) -> ShabtiDocument | None:
    return UnstructuredFileLoader.load(file, filename)
