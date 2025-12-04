from typing import Any
import httpx
from ssl import SSLContext
from urllib.parse import urljoin
from keycloak import KeycloakOpenID
from asyncio import create_task, Task
from .exceptions import ShabtiRequestError
from .codes import EXPECTED_CODES
from shabti_types import (
    AuthzCollectionInfo,
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

    async def _make_request(
        self, method, url, json=None, files=None, stream=False, params: dict = None
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
                params=params,
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
            return await self._make_request(
                method=method, url=url, json=json, files=files, stream=stream
            )

    async def _stream_request(
        self, method, url, json=None, files=None, params: dict = None
    ):
        response = await self._make_request(
            method=method, url=url, json=json, files=files, stream=True, params=params
        )
        async for line in response.aiter_lines():
            yield line
        await response.aclose()

    async def create_collection(
        self, collection_name: str, location: str, owner_username: str | None = None
    ) -> str:
        response = await self._make_request(
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
        response = await self._make_request("GET", "collections")
        return [AuthzCollectionInfo(**item) for item in response.json()]
