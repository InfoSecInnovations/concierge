import httpx
from urllib.parse import urljoin


class ConciergeClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.httpx_client = httpx.AsyncClient(timeout=None)

    async def __make_request(self, method, url, json):
        return await self.httpx_client.request(
            method=method, url=urljoin(self.server_url, url), json=json
        )

    async def create_collection(self, collection_name: str):
        response = await self.__make_request(
            "POST", "collections", {"collection_name": collection_name}
        )
        print(response.json())
        return response.json()["collection_id"]
