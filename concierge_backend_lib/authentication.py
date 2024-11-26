import requests
from keycloak import (
    KeycloakOpenID,
    KeycloakOpenIDConnection,
    KeycloakUMA,
    KeycloakAdmin,
    KeycloakAuthenticationError,
)
import os
from dotenv import load_dotenv
import urllib3
from asyncio import create_task, Task
from typing import Any


urllib3.disable_warnings()


def server_url():
    load_dotenv()
    keycloak_host = os.getenv("KEYCLOAK_HOST", "localhost")
    return f"https://{keycloak_host}:8443"


def keycloak_openid_config():
    # this disables TLS verification and warning
    # TODO: enable verification when using production settings
    session = requests.Session()
    session.verify = False
    return session.get(
        f"{server_url()}/realms/concierge/.well-known/openid-configuration"
    ).json()


def get_keycloak_client():
    load_dotenv()
    keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
    client = KeycloakOpenID(
        server_url=server_url(),
        realm_name="concierge",
        client_id=keycloak_client_id,
        client_secret_key=keycloak_client_secret,
        verify=False,
    )
    return client


def get_service_account_connection():
    load_dotenv()
    keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
    keycloak_connection = KeycloakOpenIDConnection(
        server_url=server_url(),
        realm_name="concierge",
        client_id=keycloak_client_id,
        client_secret_key=keycloak_client_secret,
        grant_type="client_credentials",
        verify=False,
    )
    return keycloak_connection


def get_keycloak_uma():
    keycloak_connection = get_service_account_connection()
    keycloak_uma = KeycloakUMA(connection=keycloak_connection)
    return keycloak_uma


def get_keycloak_admin_client():
    keycloak_connection = get_service_account_connection()
    client = KeycloakAdmin(connection=keycloak_connection)
    return client


def get_keycloak_admin_openid_token(client: KeycloakOpenID):
    token = client.token(grant_type="client_credentials")
    return token


async def get_token_info(token):
    keycloak_openid = get_keycloak_client()
    return await keycloak_openid.a_decode_token(token, validate=False)


username_cache = {}


def get_username(user_id):
    if user_id in username_cache:
        return username_cache[user_id]
    admin_client = get_keycloak_admin_client()
    user_info = admin_client.get_user(user_id)
    if "username" in user_info:
        username_cache[user_id] = user_info["username"]
        return username_cache[user_id]
    return ""


def execute_with_token(token, func):
    try:
        func(token)
        return token
    except Exception:
        keycloak_openid = get_keycloak_client()
        token = keycloak_openid.refresh_token(token["refresh_token"])
        func(token)
        return token


async def execute_async_with_token(token, func):
    try:
        await func(token)
        return token
    except KeycloakAuthenticationError:
        keycloak_openid = get_keycloak_client()
        token = await keycloak_openid.a_refresh_token(token["refresh_token"])
        await func(token)
        return token


async def get_async_result_with_token(token, func):
    try:
        result = await func(token)
        return (token, result)
    except KeycloakAuthenticationError:
        keycloak_openid = get_keycloak_client()
        token = await keycloak_openid.a_refresh_token(token["refresh_token"])
        result = await func(token)
        return (token, result)


class AsyncTokenTaskRunner:
    """
    A task runner that stores a Keycloak Oauth token and uses it to run tasks that require authentication.
    The token will automatically be refreshed as needed.
    """

    def __init__(self, token) -> None:
        self.tasks: set[Task] = set()
        self.token = token
        self.currentId = 0
        self.refresh_task: Task | None = None

    async def run_with_token(self, func, task_id=None) -> tuple[dict, Any]:
        if task_id is None:
            task_id = self.currentId
            self.currentId += 1
        token = self.token
        task = create_task(func(token))
        self.tasks.add(task)

        def on_done(task):
            self.tasks.remove(task)

        task.add_done_callback(on_done)

        try:
            if self.refresh_task:
                await self.refresh_task
            result = await task
            return (self.token, result)
        except KeycloakAuthenticationError:
            # if the token being used is still the same as the stored one, it probably expired
            if token == self.token:
                # if we're not already refreshing, we should launch the refresh task
                if self.refresh_task is None:

                    async def do_refresh():
                        keycloak_openid = get_keycloak_client()
                        self.token = await keycloak_openid.a_refresh_token(
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
            return await self.run_with_token(func, task_id)
