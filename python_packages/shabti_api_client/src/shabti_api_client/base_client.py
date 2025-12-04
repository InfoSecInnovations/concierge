from abc import ABC, abstractmethod
from shabti_types import (
    TaskInfo,
    PromptConfigInfo,
    ModelLoadInfo,
    WebFile,
    PromptChunk,
    UnsupportedFileError,
    DocumentIngestInfo,
    DocumentList,
)
import httpx
import json


class BaseShabtiClient(ABC):
    @abstractmethod
    async def _make_request(
        self,
        method,
        url,
        json=None,
        files: httpx._types.RequestFiles = None,
        params: dict = None,
    ):
        pass

    @abstractmethod
    async def _stream_request(
        self,
        method,
        url,
        json=None,
        files: httpx._types.RequestFiles = None,
        params: dict = None,
    ):
        pass

    async def api_status(self):
        try:
            response = await self._make_request("GET", "/")
            return response.status_code == 200
        except Exception:
            return False

    async def delete_collection(self, collection_id: str) -> str:
        response = await self._make_request("DELETE", f"collections/{collection_id}")
        return response.json()["collection_id"]

    async def insert_files(self, collection_id: str, file_paths: list[str]):
        async for line in self._stream_request(
            "POST",
            f"/collections/{collection_id}/documents/files",
            files=[("files", open(file_path, "rb")) for file_path in file_paths],
        ):
            json_obj = json.loads(line)
            if "error" in json_obj and json_obj["error"] == "UnsupportedFileError":
                yield UnsupportedFileError(json_obj["filename"], json_obj["message"])
                continue
            yield DocumentIngestInfo(**json_obj)

    async def insert_urls(self, collection_id: str, urls: list[str]):
        async for line in self._stream_request(
            "POST",
            f"/collections/{collection_id}/documents/urls",
            json=urls,
        ):
            yield DocumentIngestInfo(**json.loads(line))

    async def get_documents(
        self,
        collection_id: str,
        search: str | None = None,
        sort: str | None = None,
        max_results: int | None = None,
        filter_document_type: list[str] | None = None,
        page: int = 0,
    ):
        params = {}
        if search:
            params["search"] = search
        if sort:
            params["sort"] = sort
        if max_results:
            params["max_results"] = max_results
        if filter_document_type:
            params["filter_document_type"] = filter_document_type
        if page:
            params["page"] = page
        response = await self._make_request(
            "GET", f"collections/{collection_id}/documents", params=params
        )
        return DocumentList(**response.json())

    async def get_document_types(self, collection_id: str) -> list[str]:
        response = await self._make_request(
            "GET", f"collections/{collection_id}/document_types"
        )
        return response.json()

    async def delete_document(self, collection_id, document_id) -> str:
        response = await self._make_request(
            "DELETE",
            f"collections/{collection_id}/documents/{document_id}",
        )
        return response.json()["document_id"]

    async def get_tasks(self):
        response = await self._make_request("GET", "/tasks")
        return {key: TaskInfo(**value) for key, value in response.json().items()}

    async def get_personas(self):
        response = await self._make_request("GET", "/personas")
        return {
            key: PromptConfigInfo(**value) for key, value in response.json().items()
        }

    async def get_enhancers(self):
        response = await self._make_request("GET", "/enhancers")
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
            response = await self._make_request(
                "POST", "/prompt/source_file", files=[("file", open(file_path, "rb"))]
            )
            file_id = response["id"]
        async for line in self._stream_request(
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
            yield PromptChunk(**json.loads(line))

    async def ollama_status(self) -> bool:
        response = await self._make_request("GET", "status/ollama")
        return response.json()["running"]

    async def opensearch_status(self) -> bool:
        response = await self._make_request("GET", "status/opensearch")
        return response.json()["running"]

    async def load_model(self, model_name: str):
        async for line in self._stream_request(
            "POST",
            "/models/pull",
            json={"model_name": model_name},
        ):
            yield ModelLoadInfo(**json.loads(line))

    async def get_file(self, collection_id: str, doc_id: str):
        response = await self._make_request("GET", f"/files/{collection_id}/{doc_id}")
        media_type = response.headers.get("content-type")
        content_disposition = response.headers.get("content-disposition")
        return WebFile(
            bytes=await response.aread(),
            media_type=media_type,
            content_disposition=content_disposition,
        )
