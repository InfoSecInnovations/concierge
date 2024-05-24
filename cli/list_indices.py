import sys
import os

# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from concierge_backend_lib.opensearch import get_client, get_indices

client = get_client()
indices = get_indices(client)

for index in indices:
    print(index)
