from .opensearch_ingesting import insert
from .authorization import auth_enabled, authorize, UnauthorizedOperationError
from tqdm import tqdm


def insert_document(token, collection_id, document, binary):
    if auth_enabled:
        authorized = authorize(token, collection_id, "update")
        if not authorized:
            raise UnauthorizedOperationError()
    yield from insert(collection_id, document, binary)


def insert_with_tqdm(token, collection_id, document, binary):
    page_progress = tqdm(total=len(document.pages))
    for x in insert_document(token, collection_id, document, binary):
        page_progress.n = x[0] + 1
        page_progress.refresh()
    page_progress.close()
