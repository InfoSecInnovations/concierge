from typing import Literal
from .authorization import (
    authorize,
    create_resource,
    list_resources,
    delete_resource,
    auth_enabled,
    UnauthorizedOperationError,
)
from .authentication import get_token_info
from uuid import uuid4
from .opensearch import (
    create_collection_index,
    delete_collection_indices,
    create_index_mapping,
    delete_index_mapping,
    get_collection_mappings,
    get_opensearch_documents,
    delete_opensearch_document,
)
import traceback


class CollectionExistsError(Exception):
    def __init__(self, message=""):
        self.message = message


class InvalidLocationError(Exception):
    def __init__(self, message=""):
        self.message = message


def get_collections(token):
    try:
        if auth_enabled:
            available_resources = list_resources(token)
            return [
                resource
                for resource in available_resources
                if resource["type"] == "collection:shared"
                or resource["type"] == "collection:private"
            ]
        else:
            # if not using authz we get the collection info from OpenSearch
            return get_collection_mappings()
    except Exception:
        print(traceback.format_exc())


type Location = Literal["private", "shared"]


# in an unsecured instance collections don't have a location, so None is valid in that case
def create_collection(token, display_name: str, location: Location | None = None):
    try:
        print(f"creating {location or ''} collection {display_name}")
        # TODO: check if we already have a collection with same name and location
        if auth_enabled:
            # when using authz collections should always have a location
            if not location:
                raise InvalidLocationError()
            authorized = authorize(token, f"collection:{location}:create")
            if not authorized:
                raise UnauthorizedOperationError()
            token_info = get_token_info(token)
            owner_id = token_info["sub"]
            resource_id = create_resource(
                display_name, f"collection:{location}", owner_id
            )
        else:
            resource_id = uuid4()
            # if we don't have authz configured, we write the collection name mapping to OpenSearch
            create_index_mapping(resource_id, display_name)
        create_collection_index(resource_id)
        print(
            f"created {location or ''} collection {display_name} with ID {resource_id}"
        )
        return resource_id
    except Exception:
        print(traceback.format_exc())


def delete_collection(token, collection_id):
    try:
        print(f"deleting collection with ID {collection_id}")
        if auth_enabled:
            authorized = authorize(token, collection_id, "delete")
            if not authorized:
                raise UnauthorizedOperationError()
            delete_resource(collection_id)
        else:
            delete_index_mapping(collection_id)
        delete_collection_indices(collection_id)
        print(f"deleted collection with ID {collection_id}")
    except Exception:
        print(traceback.format_exc())


def get_documents(token, collection_id):
    try:
        if auth_enabled:
            authorized = authorize(token, collection_id, "read")
            if not authorized:
                raise UnauthorizedOperationError()
        return get_opensearch_documents(collection_id)
    except Exception:
        print(traceback.format_exc())


def delete_document(token, collection_id, document_type, document_id):
    try:
        if auth_enabled:
            authorized = authorize(token, collection_id, "update")
            if not authorized:
                raise UnauthorizedOperationError()
        return delete_opensearch_document(collection_id, document_type, document_id)
    except Exception:
        print(traceback.format_exc())
