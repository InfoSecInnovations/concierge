from .opensearch_ingesting import insert
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
    async for x in asyncify_generator(insert(collection_id, document, binary)):
        yield x
    if logging_enabled():
        collection_info = await get_collection_info(collection_id)
        doc = get_document(collection_id, x.document_id)
        document_info = DocumentInfo(
            source=doc["source"],
            ingest_date=doc["ingest_date"],
            vector_count=doc["vector_count"],
            document_id=doc["id"],
            page_count=doc["page_count"],
            media_type=doc["media_type"],
            filename=doc["filename"] if "filename" in doc else None,
            languages=doc["languages"] if "languages" in doc else None,
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
