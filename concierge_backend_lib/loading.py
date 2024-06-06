import sys
import os
from binaryornot.check import is_binary

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loaders.pdf import load_pdf
from loaders.text import load_text


class ConciergeDocLoader:
    # TODO: class checks if it can load file

    # TODO: load function that returns pages
    pass


def load_file(directory, filename):
    full_path = os.path.join(directory, filename)
    if filename.endswith(".pdf"):
        return load_pdf(directory, filename)
    elif not is_binary(full_path):
        try:  # generic text loader doesn't always succeed so we should catch the exception
            return load_text(directory, filename)
        except Exception:
            print(f"{full_path} was unable to be ingested as plaintext")
            return None
    print(
        f"{full_path} was unable to be loaded by any of the current Concierge loading options"
    )
    return None
