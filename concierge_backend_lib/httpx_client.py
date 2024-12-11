import httpx
import os
from dotenv import load_dotenv

load_dotenv()
httpx_client = httpx.AsyncClient(verify=os.getenv("ROOT_CA"), timeout=None)
