from loaders.base_loader import ShabtiFileLoader, ShabtiDocument
from loaders.pdf import PDFLoader
from loaders.text import TextFileLoader

loaders: list[ShabtiFileLoader] = [PDFLoader, TextFileLoader]


def load_file(full_path, filename) -> ShabtiDocument | None:
    for loader in loaders:
        if loader.can_load(full_path):
            try:
                return loader.load(full_path, filename)
            except Exception as e:
                print(e)
    print(
        f"{full_path} was unable to be loaded by any of the current Shabti loading options"
    )
    return None
