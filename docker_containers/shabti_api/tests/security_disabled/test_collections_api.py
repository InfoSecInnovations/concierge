import os
from ...src.app.functionality.document_collections import (
    get_collections,
    get_documents,
)
from shabti_util import auth_enabled
import pytest
import secrets

filename = "test_doc.txt"
file_path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)


def test_auth_setting():
    assert not auth_enabled()


async def test_create_collection(shabti_client):
    collection_name = secrets.token_hex(8)
    response = shabti_client.post(
        "/collections", json={"collection_name": collection_name}
    )
    assert response.status_code == 201
    collection_id = response.json()["collection_id"]
    assert collection_id
    # after checking we got the expected type of response, also check the collection actually exists
    collections = await get_collections(None)
    assert next(
        (
            collection_info
            for collection_info in collections
            if collection_info.collection_id == collection_id
            and collection_info.collection_name == collection_name
        ),
        None,
    )


async def test_list_collections(shabti_client, shabti_collection_id):
    response = shabti_client.get("/collections")
    assert response.status_code == 200
    assert next(
        (
            collection_info
            for collection_info in response.json()
            if collection_info["collection_id"] == shabti_collection_id
        ),
        None,
    )


async def test_insert_documents(shabti_client, shabti_collection_id):
    response = shabti_client.post(
        f"/collections/{shabti_collection_id}/documents/files",
        files=[("files", open(file_path, "rb"))],
    )
    assert response.status_code == 200
    docs = await get_documents(None, shabti_collection_id)
    assert next((doc for doc in docs.documents if doc.filename == filename), None)


url = "https://www.scrapethissite.com/pages/simple/"
# the listing page above `url`, which unlike `url` itself has children within the crawl scope
listing_url = "https://www.scrapethissite.com/pages/"


async def test_insert_urls(shabti_client, shabti_collection_id):
    response = shabti_client.post(
        f"/collections/{shabti_collection_id}/documents/urls", json=[url]
    )
    assert response.status_code == 200
    docs = await get_documents(None, shabti_collection_id)
    doc = next((doc for doc in docs.documents if doc.source == url), None)
    assert doc
    # the default is the page that was asked for, not the whole site
    assert doc.page_count == 1
    assert doc.vector_count > 1
    # the page is a list of 250 countries, and "Zimbabwe" is the last of them. the document search
    # matches child text, so this proves the whole listing survived extraction and chunking rather
    # than being cut down to the handful of rows main content extraction used to keep
    found = await get_documents(None, shabti_collection_id, search="Zimbabwe")
    assert found.documents


async def test_insert_urls_with_depth(shabti_client, shabti_collection_id):
    response = shabti_client.post(
        f"/collections/{shabti_collection_id}/documents/urls",
        json=[listing_url],
        params={"max_depth": 2},
    )
    assert response.status_code == 200
    docs = await get_documents(None, shabti_collection_id)
    doc = next((doc for doc in docs.documents if doc.source == listing_url), None)
    assert doc
    # the listing plus the five pages it links to, all under /pages/
    assert doc.page_count >= 5
    # "Zimbabwe" appears only on the /pages/simple/ child and not on the listing itself, so finding
    # it proves a linked page was actually crawled rather than just the seed
    assert (
        await get_documents(None, shabti_collection_id, search="Zimbabwe")
    ).documents
    # "internet" appears only on the site root, which is above the crawl scope. finding it would
    # mean the crawl had widened past the URL it was given
    assert not (
        await get_documents(None, shabti_collection_id, search="internet")
    ).documents


async def test_document_counts_are_per_document(shabti_client, shabti_collection_id):
    response = shabti_client.post(
        f"/collections/{shabti_collection_id}/documents/files",
        files=[("files", open(file_path, "rb"))],
    )
    assert response.status_code == 200
    response = shabti_client.post(
        f"/collections/{shabti_collection_id}/documents/urls",
        json=[listing_url],
        params={"max_depth": 2},
    )
    assert response.status_code == 200
    docs = await get_documents(None, shabti_collection_id)
    file_doc = next((doc for doc in docs.documents if doc.filename == filename), None)
    crawled_doc = next(
        (doc for doc in docs.documents if doc.source == listing_url), None
    )
    assert file_doc and crawled_doc
    # the counts for a listing come from one aggregation over every document on the page, so each
    # document has to get its own bucket rather than the whole page sharing a count
    assert file_doc.page_count == 1
    assert crawled_doc.page_count >= 5
    assert file_doc.vector_count > 0
    assert crawled_doc.vector_count > 0


@pytest.mark.parametrize(
    "forbidden_url",
    [
        "http://127.0.0.1:9200/",
        "http://169.254.169.254/latest/meta-data/",
    ],
)
async def test_insert_urls_rejects_internal_addresses(
    shabti_client, shabti_collection_id, forbidden_url
):
    response = shabti_client.post(
        f"/collections/{shabti_collection_id}/documents/urls", json=[forbidden_url]
    )
    assert response.status_code == 403
    assert response.json()["error_type"] == "ForbiddenUrlError"
    docs = await get_documents(None, shabti_collection_id)
    assert not docs.documents


async def test_delete_document(shabti_client, shabti_collection_id, shabti_document_id):
    docs = await get_documents(None, shabti_collection_id)
    # test the document is actually there before deleting it
    assert next(
        (doc for doc in docs.documents if doc.document_id == shabti_document_id), None
    )
    response = shabti_client.delete(
        f"/collections/{shabti_collection_id}/documents/{shabti_document_id}"
    )
    assert response.status_code == 200
    docs = await get_documents(None, shabti_collection_id)
    assert not any(doc.document_id == shabti_document_id for doc in docs.documents)


async def test_delete_collection(shabti_client, shabti_collection_id):
    response = shabti_client.delete(f"/collections/{shabti_collection_id}")
    assert response.status_code == 200
    collections = await get_collections(None)
    response_json = response.json()
    assert not any(
        collection.collection_id == response_json["collection_id"]
        for collection in collections
    )
