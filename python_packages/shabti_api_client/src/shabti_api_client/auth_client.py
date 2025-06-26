from typing import Any
import httpx
from ssl import SSLContext
from urllib.parse import urljoin
from keycloak import KeycloakOpenID
from asyncio import create_task, Task
from .exceptions import ShabtiRequestError
from .codes import EXPECTED_CODES
import json
from shabti_types import (
    AuthzCollectionInfo,
    DocumentInfo,
    DocumentIngestInfo,
    TaskInfo,
    PromptConfigInfo,
    ModelLoadInfo,
    WebFile,
)
from .base_client import BaseShabtiClient
from .raise_error import raise_error


class ShabtiAuthenticationError(ShabtiRequestError):
    pass


class ShabtiTokenExpiredError(ShabtiRequestError):
    pass


class ShabtiAuthorizationClient(BaseShabtiClient):
    def __init__(
        self,
        server_url: str,
        token: Any,
        keycloak_client: KeycloakOpenID,
        verify: SSLContext | None = None,
    ):
        self.server_url = server_url
        self.httpx_client = httpx.AsyncClient(verify=verify, timeout=None)
        self.token = token
        self.keycloak_client = keycloak_client
        self.refresh_task: Task | None = None

    async def __make_request(
        self, method, url, json=None, files=None, stream=False
    ) -> httpx.Response:
        async def make_request(token):
            headers = (
                {"Authorization": f"Bearer {token['access_token']}"} if token else None
            )
            request = self.httpx_client.build_request(
                method=method,
                url=urljoin(self.server_url, url),
                headers=headers,
                json=json,
                files=files,
            )
            response = await self.httpx_client.send(request, stream=stream)
            if response.status_code == 401:
                raise ShabtiTokenExpiredError(status_code=401)
            if response.status_code == 403:
                raise ShabtiAuthenticationError(status_code=403)
            if response.status_code not in EXPECTED_CODES:
                await response.aread()
                raise_error(response)
            return response

        token = self.token
        task = create_task(make_request(token))

        try:
            if self.refresh_task:
                await self.refresh_task
            result = await task
            return result
        except ShabtiTokenExpiredError:
            # if the token being used is still the same as the stored one, it probably expired
            if token == self.token:
                # if we're not already refreshing, we should launch the refresh task
                if self.refresh_task is None:

                    async def do_refresh():
                        self.token = await self.keycloak_client.a_refresh_token(
                            self.token["refresh_token"]
                        )

                    self.refresh_task = create_task(do_refresh())

                    # unset refresh task when done
                    def on_done(_):
                        self.refresh_task = None

                    self.refresh_task.add_done_callback(on_done)
                # once we've ensured a refresh task is running, wait for it to complete
                await self.refresh_task
            # if not it has probably been refreshed and we're good to go
            # try to rerun using current token
            return await self.__make_request(
                method=method, url=url, json=json, files=files, stream=stream
            )

    async def __stream_request(self, method, url, json=None, files=None):
        response = await self.__make_request(
            method=method, url=url, json=json, files=files, stream=True
        )
        async for line in response.aiter_lines():
            yield line
        await response.aclose()

    async def api_status(self):
        try:
            response = await self.__make_request("GET", "/")
            return response.status_code == 200
        except Exception:
            return False

    async def create_collection(
        self, collection_name: str, location: str, owner_username: str | None = None
    ) -> str:
        response = await self.__make_request(
            "POST",
            "collections",
            {
                "collection_name": collection_name,
                "location": location,
                "owner_username": owner_username,
            },
        )
        return response.json()["collection_id"]

    async def get_collections(self):
        response = await self.__make_request("GET", "collections")
        return [AuthzCollectionInfo(**item) for item in response.json()]

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
            "POST", f"/collections/{collection_id}/documents/urls", json=urls
        ):
            yield DocumentIngestInfo(**json.loads(line))

    async def delete_document(self, collection_id, document_id) -> str:
        response = await self.__make_request(
            "DELETE",
            f"collections/{collection_id}/documents/{document_id}",
        )
        return response.json()["document_id"]

    async def get_collection_scopes(self, collection_id: str):
        response = await self.__make_request("GET", f"/{collection_id}/scopes")
        return set(response.json())

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

    async def get_user_info(self):
        response = await self.__make_request("GET", "/user_info")
        return response.json()

    async def get_permissions(self):
        response = await self.__make_request("GET", "/permissions")
        return set(response.json())

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
