from concierge_api_client.auth_client import ConciergeAuthorizationClient
import asyncio
from concierge_scripts.load_dotenv import load_env
import ssl
import os
from docker_containers.concierge_api.app.authentication import get_keycloak_client

load_env()

keycloak_client = get_keycloak_client()
token = keycloak_client.token("testadmin", "test")

client = ConciergeAuthorizationClient(
    server_url="http://127.0.0.1:8000",
    verify=ssl.create_default_context(cafile=os.getenv("ROOT_CA")),
    keycloak_client=keycloak_client,
    token=token,
)

collection_id = None
document_id = None

filename = "test_doc.txt"
file_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "docker_containers",
    "concierge_api",
    "tests",
    "assets",
    filename,
)


async def test_user_info():
    info = await client.get_user_info()
    print(info)


async def test_collection_create():
    global collection_id
    collection_id = await client.create_collection("stlbl", "private")
    print(collection_id)


async def test_list_collections():
    collections = await client.get_collections()
    print(collections)


async def test_insert_document():
    global document_id
    async for line in client.insert_files(collection_id, [file_path]):
        print(line)
        document_id = line.document_id


async def test_insert_urls():
    async for line in client.insert_urls(
        collection_id,
        ["https://en.wikipedia.org/wiki/Generative_artificial_intelligence"],
    ):
        print(line)


async def test_list_documents():
    documents = await client.get_documents(collection_id)
    print(documents)


async def test_prompt():
    async for line in client.prompt(
        collection_id, "Where does Generative AI get its data from?", "question"
    ):
        print(line)


async def test_delete_document():
    deleted_document_id = await client.delete_document(
        collection_id, "plaintext", document_id
    )
    print(deleted_document_id)


async def test_collection_delete():
    deleted_collection_id = await client.delete_collection(collection_id)
    print(deleted_collection_id)


async def run_all():
    await test_user_info()
    await test_collection_create()
    await test_list_collections()
    await test_insert_document()
    await test_insert_urls()
    await test_list_documents()
    await test_prompt()
    await test_delete_document()
    await test_collection_delete()


asyncio.run(run_all())
