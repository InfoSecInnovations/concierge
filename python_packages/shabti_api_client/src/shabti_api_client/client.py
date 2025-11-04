import httpx
from urllib.parse import urljoin
from .codes import EXPECTED_CODES
from shabti_types import (
    CollectionInfo,
)
from .base_client import BaseShabtiClient
from .raise_error import raise_error


class ShabtiClient(BaseShabtiClient):
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.httpx_client = httpx.AsyncClient(timeout=None)

    async def _make_request(
        self, method, url, json=None, files: httpx._types.RequestFiles = None
    ):
        response = await self.httpx_client.request(
            method=method, url=urljoin(self.server_url, url), json=json, files=files
        )
        if response.status_code not in EXPECTED_CODES:
            raise_error(response)
        return response

    async def _stream_request(
        self, method, url, json=None, files: httpx._types.RequestFiles = None
    ):
        async with self.httpx_client.stream(
            method=method, url=urljoin(self.server_url, url), json=json, files=files
        ) as response:
            if response.status_code not in EXPECTED_CODES:
                await response.aread()
                raise_error(response)
            async for line in response.aiter_lines():
                yield line

    async def create_collection(self, collection_name: str) -> str:
        response = await self._make_request(
            "POST", "collections", {"collection_name": collection_name}
        )
        return response.json()["collection_id"]

    async def get_collections(self):
        response = await self._make_request("GET", "collections")
        return [CollectionInfo(**item) for item in response.json()]
