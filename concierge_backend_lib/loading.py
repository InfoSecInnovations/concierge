import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loaders.base_loader import ConciergeFileLoader, ConciergeDocument
from loaders.pdf import PDFLoader
from loaders.text import TextFileLoader

loaders: list[ConciergeFileLoader] = [PDFLoader, TextFileLoader]


def load_file(full_path) -> ConciergeDocument | None:
    for loader in loaders:
        if loader.can_load(full_path):
            try:
                return loader.load(full_path)
            except Exception as e:
                print(e)
    print(
        f"{full_path} was unable to be loaded by any of the current Concierge loading options"
    )
    return None
