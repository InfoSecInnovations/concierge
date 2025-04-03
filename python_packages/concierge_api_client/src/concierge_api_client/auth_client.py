from typing import Any
import httpx
from ssl import SSLContext
from urllib.parse import urljoin
from keycloak import KeycloakOpenID
from asyncio import create_task, Task
from .exceptions import ConciergeRequestError
from .codes import EXPECTED_CODES


class ConciergeAuthenticationError(ConciergeRequestError):
    pass


class ConciergeTokenExpiredError(ConciergeRequestError):
    pass


class ConciergeAuthorizationClient:
    def __init__(
        self,
        server_url: str,
        verify: SSLContext | None = None,
        token: None | Any = None,
        keycloak_client: None | KeycloakOpenID = None,
    ):
        self.server_url = server_url
        self.httpx_client = httpx.AsyncClient(verify=verify, timeout=None)
        self.token = token
        self.keycloak_client = keycloak_client
        self.tasks: set[Task] = set()
        self.currentId = 0
        self.refresh_task: Task | None = None

    async def __request_with_token(
        self, method, url, json=None, task_id=None
    ) -> httpx.Response:
        if task_id is None:
            task_id = self.currentId
            self.currentId += 1
        token = self.token

        async def make_request(token):
            headers = (
                {"Authorization": f"Bearer {token['access_token']}"} if token else None
            )
            response = await self.httpx_client.request(
                method=method,
                url=urljoin(self.server_url, url),
                headers=headers,
                json=json,
            )
            print(response)
            if response.status_code == 401:
                raise ConciergeTokenExpiredError(status_code=401)
            if response.status_code == 403:
                raise ConciergeAuthenticationError(status_code=403)
            if response.status_code not in EXPECTED_CODES:
                raise ConciergeRequestError(status_code=response.status_code)
            return response

        task = create_task(make_request(token))
        self.tasks.add(task)

        def on_done(task):
            self.tasks.remove(task)

        task.add_done_callback(on_done)

        try:
            if self.refresh_task:
                await self.refresh_task
            result = await task
            return result
        except ConciergeTokenExpiredError:
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
            return await self.__request_with_token(method, url, json, task_id)

    async def create_collection(self, collection_name: str, location: str):
        response = await self.__request_with_token(
            "POST",
            "collections",
            {"collection_name": collection_name, "location": location},
        )
        return response.json()["collection_id"]
