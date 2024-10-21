from .opensearch_ingesting import insert
from .authorization import auth_enabled, authorize, UnauthorizedOperationError


def insert_document(token, collection_id, document, binary):
    if auth_enabled:
        authorized = authorize(token, collection_id, "update")
        if not authorized:
            raise UnauthorizedOperationError()
    yield from insert(collection_id, document, binary)
