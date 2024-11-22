import httpx

# TODO: enable verify if using production settings
httpx_client = httpx.AsyncClient(verify=False, timeout=None)
