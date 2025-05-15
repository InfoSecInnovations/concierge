# This test should be run once Shabti is installed with the demo RBAC configuration
# For best results it should be fresh installation with no collections created or tweaks made to the access controls
# The web app must be served as HTTPS on localhost port 15130
# Do not use this on a production instance!
# import asyncio
# import requests
# from .lib import clean_up_collections, create_collection_for_user, ingest_document
# from concierge_shiny.oauth2 import set_token_cookies
# from concierge_backend_lib.authentication import (
#     get_keycloak_client,
# )
# import os

# collection_id = None
# doc_id = None


# async def create_collection_and_doc():
#     global collection_id
#     global doc_id
#     collection_id = await create_collection_for_user(
#         "testadmin", "private", "test_docs"
#     )
#     doc_id = await ingest_document("testadmin", collection_id)
#     print("doc ID")
#     print(doc_id)


# def setup_module():
#     asyncio.run(create_collection_and_doc())


# class DummyResponse:
#     def __init__(self) -> None:
#         self.cookies = {}

#     def set_cookie(self, key, value, httponly):
#         self.cookies[key] = str(value)


# def request_with_user(username, url):
#     keycloak_client = get_keycloak_client()
#     token = keycloak_client.token(username, "test")
#     cookie_response = DummyResponse()
#     set_token_cookies(token, cookie_response)
#     response = requests.get(
#         url, cookies=cookie_response.cookies, verify=os.getenv("ROOT_CA")
#     )
#     return response


# def test_can_access_files_route():
#     response = request_with_user(
#         "testadmin",
#         f"https://localhost:15130/files/{collection_id}/plaintext/{doc_id}",
#     )
#     assert response.status_code == 200


# def test_other_user_cannot_access_files_route():
#     response = request_with_user(
#         "testshared",
#         f"https://localhost:15130/files/{collection_id}/plaintext/{doc_id}",
#     )
#     assert response.status_code == 403


# def teardown_module():
#     asyncio.run(clean_up_collections())
