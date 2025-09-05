from ..loaders.base_loader import ShabtiDocument
from ..loaders.unstructured import UnstructuredFileLoader


def load_file(full_path, filename) -> ShabtiDocument | None:
    return UnstructuredFileLoader.load(full_path, filename)
