from opensearchpy import helpers
from .embeddings import create_embeddings
from .loaders.base_loader import ShabtiDocument
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


def insert(
    collection_id: str,
    document: ShabtiDocument,
    binary_path: str | None = None,
):
    tokenizer = Tokenizer.from_pretrained(
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )
    # read the capacity before clearing truncation, which sets `truncation` to None
    capacity = tokenizer.truncation["max_length"]
    # semantic-text-splitter >=0.31 reports the *truncated* token count for tokenizers with
    # truncation enabled, so oversized text measures exactly `capacity` and is never split
    tokenizer.no_truncation()
    splitter = TextSplitter.from_huggingface_tokenizer(tokenizer, capacity, overlap=50)

    total = len(document.pages)
    if not total:
        raise EmptyDocumentError(source=document.metadata.source)

    client = get_client()
    additional = {}
    if binary_path:
        additional["binary_path"] = binary_path

    doc_id = client.index(
        index=collection_id,
        body={
            "type": "document",
            "child_item_to_document": "document",
            **vars(document.metadata),
            **additional,
        },
        refresh=True,
    )["_id"]

    try:
        for index, page in enumerate(document.pages):
            page_id = client.index(
                index=collection_id,
                body={
                    "child_item_to_document": {"name": "child_item", "parent": doc_id},
                    "type": "page",
                    **vars(page.metadata),
                },
                routing=doc_id,
                refresh=True,
            )["_id"]
            chunks = [
                chunk for chunk in splitter.chunks(page.content) if chunk.strip()
            ]  # don't allow empty or whitespace chunks
            vects = create_embeddings(chunks)
            # flush per page rather than accumulating every vector for every page: a crawl or a large
            # text file can be thousands of chunks of 768 floats. the rollback below deletes children
            # by parent, so already flushed vectors are still cleaned up on failure.
            helpers.bulk(
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
                        "text": chunks[index],
                        "document_vector": vect,
                        "page_id": page_id,
                        "doc_id": doc_id,
                    }
                    for index, vect in enumerate(vects)
                ],
                refresh=True,
            )
            yield DocumentIngestInfo(
                progress=index,
                total=total,
                document_id=doc_id,
                document_type=document.metadata.media_type,
                label=document.metadata.filename
                if document.metadata.filename
                else document.metadata.source,
            )

    except Exception as e:
        delete_opensearch_document(collection_id, doc_id)
        raise e
