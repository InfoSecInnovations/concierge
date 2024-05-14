import sys
import os
# on Linux the parent directory isn't automatically included for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from concierge_backend_lib.opensearch import get_client

client = get_client()
response = list(client.indices.get_alias("*").keys())

print(response)