from opensearch_ingesting import insert
from authorization import auth_enabled, authorize, UnauthorizedOperationError
from tqdm import tqdm
from isi_util.async_generator import asyncify_generator
from models import DocumentIngestInfo
from typing import AsyncGenerator, Any


async def insert_document(
    token, collection_id, document, binary=None
) -> AsyncGenerator[DocumentIngestInfo, Any]:
    if auth_enabled():
        authorized = await authorize(token, collection_id, "update")
        if not authorized:
            raise UnauthorizedOperationError()
    async for x in asyncify_generator(insert(collection_id, document, binary)):
        yield x


async def insert_with_tqdm(token, collection_id, document, binary=None):
    page_progress = tqdm(total=len(document.pages))
    async for progress, total, doc_id in insert_document(
        token, collection_id, document, binary
    ):
        page_progress.n = progress + 1
        page_progress.refresh()
    page_progress.close()
    return doc_id
