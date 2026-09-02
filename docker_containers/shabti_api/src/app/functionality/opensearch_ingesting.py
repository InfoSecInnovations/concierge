import asyncio
from contextlib import aclosing, suppress
from functools import cache
from opensearchpy.helpers import async_bulk
from .embeddings import create_embeddings, get_embeddings_model_id
from .loaders.base_loader import ShabtiDocument, ShabtiPageStream
from .opensearch import get_client, delete_opensearch_document
from shabti_types import DocumentIngestInfo, EmptyDocumentError
from semantic_text_splitter import TextSplitter
from tokenizers import Tokenizer


def get_field_type(python_type):
    if python_type == "int":
        return "long"
    if python_type == "float":
        return "float"
    if python_type == "bool":
        return "boolean"
    return "keyword"


@cache
def get_splitter() -> TextSplitter:
    tokenizer = Tokenizer.from_pretrained(
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )
    # read the capacity before clearing truncation, which sets `truncation` to None
    capacity = tokenizer.truncation["max_length"]
    # semantic-text-splitter >=0.31 reports the *truncated* token count for tokenizers with
    # truncation enabled, so oversized text measures exactly `capacity` and is never split
    tokenizer.no_truncation()
    return TextSplitter.from_huggingface_tokenizer(tokenizer, capacity, overlap=50)


async def insert(
    collection_id: str,
    stream: ShabtiPageStream,
    binary_path: str | None = None,
):
    """Embed and index a document's pages as the loader produces them.

    OpenSearch is awaited directly; the splitter and the embeddings server are blocking, so they
    run in threads and the event loop stays free for the loader: a crawl keeps fetching while the
    page before it is being embedded. Within a document each page's write is left running as a
    task, which overlaps the two servers involved: a page is embedded while the previous one's
    vectors are still being written to OpenSearch.
    """
    client = get_client()
    # both are per-document rather than per-page: the model listing is a round trip and the
    # tokenizer is a download, and neither changes while one document is being ingested
    model_id = await asyncio.to_thread(get_embeddings_model_id)
    splitter = await asyncio.to_thread(get_splitter)

    label = stream.metadata.filename or stream.metadata.source
    doc_id: str | None = None
    pending: asyncio.Task | None = None
    # the page whose write is in flight, which is also the next one to report progress for
    written = -1

    async def create_parent() -> str:
        additional = {"binary_path": binary_path} if binary_path else {}
        return (
            await client.index(
                index=collection_id,
                body={
                    "type": "document",
                    "child_item_to_document": "document",
                    **vars(stream.metadata),
                    **additional,
                },
            )
        )["_id"]

    def split(page: ShabtiDocument.ShabtiPage) -> list[str]:
        # don't allow empty or whitespace chunks
        return [chunk for chunk in splitter.chunks(page.content) if chunk.strip()]

    async def write(page: ShabtiDocument.ShabtiPage, chunks: list[str], vects) -> None:
        page_id = (
            await client.index(
                index=collection_id,
                body={
                    "child_item_to_document": {"name": "child_item", "parent": doc_id},
                    "type": "page",
                    **vars(page.metadata),
                },
                routing=doc_id,
            )
        )["_id"]
        # flush per page rather than accumulating every vector for every page: a crawl or a large
        # text file can be thousands of chunks of 768 floats. the rollback below deletes children
        # by parent, so already flushed vectors are still cleaned up on failure.
        await async_bulk(
            client,
            [
                {
                    "_index": collection_id,
                    "_routing": doc_id,
                    "child_item_to_document": {
                        "name": "child_item",
                        "parent": doc_id,
                    },
                    "type": "vector",
                    "text": chunk,
                    "document_vector": vect,
                    "page_id": page_id,
                    "doc_id": doc_id,
                }
                for chunk, vect in zip(chunks, vects)
            ],
        )

    def progress() -> DocumentIngestInfo:
        return DocumentIngestInfo(
            progress=written,
            total=stream.estimated_total(),
            document_id=doc_id,
            document_type=stream.metadata.media_type,
            label=label,
        )

    try:
        # closed explicitly rather than left to the garbage collector: a crawl stream shuts its
        # crawler down from there, and it has to happen when this loop ends however it ends
        async with aclosing(stream.pages) as source:
            async for page in source:
                if doc_id is None:
                    # created on the first page rather than up front, so a source that turns out to
                    # be empty leaves nothing behind to clean up
                    doc_id = await create_parent()
                chunks = await asyncio.to_thread(split, page)
                vects = await asyncio.to_thread(create_embeddings, chunks, model_id)
                if pending:
                    await pending
                    yield progress()
                written += 1
                pending = asyncio.create_task(write(page, chunks, vects))

        if pending:
            await pending
            yield progress()

        if doc_id is None:
            raise EmptyDocumentError(source=stream.metadata.source)

        # nothing above refreshes, so this is what makes the document searchable and what the
        # vector and page counts read straight after an ingest depend on
        await client.indices.refresh(index=collection_id)

    except Exception as e:
        if pending:
            # awaited rather than cancelled: cancelling part way through the bulk would let the
            # rest of it land after the rollback had already run, leaving orphaned vectors behind
            with suppress(Exception):
                await pending
        if doc_id is not None:
            await delete_opensearch_document(collection_id, doc_id)
        raise e
