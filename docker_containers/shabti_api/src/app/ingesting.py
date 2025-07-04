from .opensearch_ingesting import insert
from .authorization import authorize, UnauthorizedOperationError
from tqdm import tqdm
from isi_util.async_generator import asyncify_generator
from shabti_types import DocumentIngestInfo, DocumentInfo
from typing import AsyncGenerator, Any
from shabti_util import auth_enabled
from .shabti_logging import log_action, log_user_action, logging_enabled
from .document_collections import get_collection_info
from .opensearch import get_document


async def insert_document(
    token, collection_id, document, binary=None
) -> AsyncGenerator[DocumentIngestInfo, Any]:
    if auth_enabled():
        authorized = await authorize(token, collection_id, "update")
        if not authorized:
            raise UnauthorizedOperationError()
    async for x in asyncify_generator(insert(collection_id, document, binary)):
        yield x
    if logging_enabled():
        collection_info = await get_collection_info(collection_id)
        # TODO: instead of making some janky version of DocumentInfo just get DocumentInfo!
        doc = get_document(collection_id, x.document_id)
        document_info = DocumentInfo(
            type=doc["type"],
            source=doc["source"],
            ingest_date=doc["ingest_date"],
            vector_count=doc["vector_count"],
            document_id=doc["doc_lookup_id"],
            page_count=doc["page_count"],
            media_type=doc["media_type"] if "media_type" in doc else None,
            filename=doc["filename"] if "filename" in doc else None,
        )
        if auth_enabled():
            await log_user_action(
                token,
                "INSERT DOCUMENT",
                f"Ingest document with ID {x.document_id} into collection with ID {collection_id}",
                collection=collection_info.model_dump(),
                document=document_info.model_dump(),
            )
        else:
            await log_action(
                "INSERT DOCUMENT",
                f"Ingest document with ID {x.document_id} into collection with ID {collection_id}",
                collection=collection_info.model_dump(),
                document=document_info.model_dump(),
            )


async def insert_with_tqdm(token, collection_id, document, binary=None):
    page_progress = tqdm(total=len(document.pages))
    async for progress, total, doc_id in insert_document(
        token, collection_id, document, binary
    ):
        page_progress.n = progress + 1
        page_progress.refresh()
    page_progress.close()
    return doc_id
