import httpx
from urllib.parse import urljoin
from .exceptions import ConciergeRequestError
from .codes import EXPECTED_CODES
import json


class ConciergeClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.httpx_client = httpx.AsyncClient(timeout=None)

    async def __make_request(
        self, method, url, json=None, files: httpx._types.RequestFiles = None
    ):
        response = await self.httpx_client.request(
            method=method, url=urljoin(self.server_url, url), json=json, files=files
        )
        if response.status_code not in EXPECTED_CODES:
            raise ConciergeRequestError(status_code=response.status_code)
        return response

    async def create_collection(self, collection_name: str):
        response = await self.__make_request(
            "POST", "collections", {"collection_name": collection_name}
        )
        return response.json()["collection_id"]

    async def get_collections(self):
        response = await self.__make_request("GET", "collections")
        return response.json()

    async def delete_collection(self, collection_id: str):
        response = await self.__make_request("DELETE", f"collections/{collection_id}")
        return response.json()["collection_id"]

    async def get_documents(self, collection_id: str):
        response = await self.__make_request(
            "GET", f"collections/{collection_id}/documents"
        )
        return response.json()

    async def insert_files(self, collection_id: str, file_paths: list[str]):
        response = await self.__make_request(
            "POST",
            f"/collections/{collection_id}/documents/files",
            files=[("files", open(file_path, "rb")) for file_path in file_paths],
        )
        async for line in response.aiter_lines():
            yield json.loads(line)
