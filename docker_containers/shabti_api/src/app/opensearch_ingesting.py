from opensearchpy import helpers
from langchain.text_splitter import SentenceTransformersTokenTextSplitter
from .embeddings import create_embeddings
from ..loaders.base_loader import ShabtiDocument
from .opensearch import get_client, delete_opensearch_document
from shabti_types import DocumentIngestInfo

splitter = SentenceTransformersTokenTextSplitter(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)


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
    binary: bytes | None = None,
):
    client = get_client()
    entries = []

    additional = {}
    if binary:
        additional["binary_data"] = binary.hex()

    doc_id = client.index(
        index=collection_id,
        body={
            "type": "document",
            "child_item_to_document": "document",
            **vars(document.metadata),
        },
        refresh=True,
    )["_id"]

    total = len(document.pages)
    if not total:  # this shouldn't really happen
        print("document has no pages!")
        return

    try:
        page = document.pages[0]

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
            chunks = splitter.split_text(page.content)
            vects = create_embeddings(chunks)
            entries.extend(
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
                ]
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
        helpers.bulk(client, entries, refresh=True)

    except Exception as e:
        delete_opensearch_document(collection_id, doc_id)
        raise e
