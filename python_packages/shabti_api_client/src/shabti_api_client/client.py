import httpx
from urllib.parse import urljoin
from .codes import EXPECTED_CODES
import json
from shabti_types import (
    CollectionInfo,
    DocumentInfo,
    DocumentIngestInfo,
    TaskInfo,
    PromptConfigInfo,
    ModelLoadInfo,
    WebFile,
)
from .base_client import BaseShabtiClient
from .raise_error import raise_error


class ShabtiClient(BaseShabtiClient):
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
            raise_error(response)
        return response

    async def __stream_request(
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

    async def api_status(self):
        try:
            response = await self.__make_request("GET", "/")
            return response.status_code == 200
        except Exception:
            return False

    async def create_collection(self, collection_name: str) -> str:
        response = await self.__make_request(
            "POST", "collections", {"collection_name": collection_name}
        )
        return response.json()["collection_id"]

    async def get_collections(self):
        response = await self.__make_request("GET", "collections")
        return [CollectionInfo(**item) for item in response.json()]

    async def delete_collection(self, collection_id: str) -> str:
        response = await self.__make_request("DELETE", f"collections/{collection_id}")
        return response.json()["collection_id"]

    async def get_documents(self, collection_id: str):
        response = await self.__make_request(
            "GET", f"collections/{collection_id}/documents"
        )
        return [DocumentInfo(**item) for item in response.json()]

    async def insert_files(self, collection_id: str, file_paths: list[str]):
        async for line in self.__stream_request(
            "POST",
            f"/collections/{collection_id}/documents/files",
            files=[("files", open(file_path, "rb")) for file_path in file_paths],
        ):
            yield DocumentIngestInfo(**json.loads(line))

    async def insert_urls(self, collection_id: str, urls: list[str]):
        async for line in self.__stream_request(
            "POST",
            f"/collections/{collection_id}/documents/urls",
            json=urls,
        ):
            yield DocumentIngestInfo(**json.loads(line))

    async def delete_document(self, collection_id, document_id) -> str:
        response = await self.__make_request(
            "DELETE",
            f"collections/{collection_id}/documents/{document_id}",
        )
        return response.json()["document_id"]

    async def get_tasks(self):
        response = await self.__make_request("GET", "/tasks")
        return {key: TaskInfo(**value) for key, value in response.json().items()}

    async def get_personas(self):
        response = await self.__make_request("GET", "/personas")
        return {
            key: PromptConfigInfo(**value) for key, value in response.json().items()
        }

    async def get_enhancers(self):
        response = await self.__make_request("GET", "/enhancers")
        return {
            key: PromptConfigInfo(**value) for key, value in response.json().items()
        }

    async def prompt(
        self,
        collection_id: str,
        prompt: str,
        task: str,
        persona: str | None = None,
        enhancers: list[str] | None = None,
        file_path: str | None = None,
    ):
        file_id = None
        if file_path:
            response = await self.__make_request(
                "POST", "/prompt/source_file", files=[("file", open(file_path, "rb"))]
            )
            file_id = response["id"]
        async for line in self.__stream_request(
            "POST",
            "prompt",
            json={
                "collection_id": collection_id,
                "user_input": prompt,
                "task": task,
                "persona": persona,
                "enhancers": enhancers,
                "file_id": file_id,
            },
        ):
            yield json.loads(line)

    async def ollama_status(self) -> bool:
        response = await self.__make_request("GET", "status/ollama")
        return response.json()["running"]

    async def opensearch_status(self) -> bool:
        response = await self.__make_request("GET", "status/opensearch")
        return response.json()["running"]

    async def load_model(self, model_name: str):
        async for line in self.__stream_request(
            "POST",
            "/models/pull",
            json={"model_name": model_name},
        ):
            yield ModelLoadInfo(**json.loads(line))

    async def get_file(self, collection_id: str, doc_id: str):
        response = await self.__make_request("GET", f"/files/{collection_id}/{doc_id}")
        media_type = response.headers.get("content-type")
        return WebFile(bytes=await response.aread(), media_type=media_type)
