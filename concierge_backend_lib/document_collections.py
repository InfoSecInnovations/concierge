from typing import Literal
from .authorization import (
    authorize,
    create_resource,
    list_resources,
    list_scopes,
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
from isi_util.async_single import asyncify


class CollectionExistsError(Exception):
    def __init__(self, message=""):
        self.message = message


class InvalidLocationError(Exception):
    def __init__(self, message=""):
        self.message = message


async def get_collections(token):
    if auth_enabled:
        available_resources = await list_resources(token)
        return [
            resource
            for resource in available_resources
            if (
                resource["type"] == "collection:shared"
                or resource["type"] == "collection:private"
            )
            and not resource["_id"].startswith(
                "default-"
            )  # the default resources are just there to show permissions if no collections are present
        ]
    else:
        # if not using authz we get the collection info from OpenSearch
        return await asyncify(get_collection_mappings)


type Location = Literal["private", "shared"]


# in an unsecured instance collections don't have a location, so None is valid in that case
async def create_collection(token, display_name: str, location: Location | None = None):
    print(f"creating {location or ''} collection {display_name}")
    # TODO: check if we already have a collection with same name and location
    if auth_enabled:
        # when using authz collections should always have a location
        if not location:
            raise InvalidLocationError()
        authorized = await authorize(token, f"collection:{location}:create")
        if not authorized:
            raise UnauthorizedOperationError()
        token_info = await get_token_info(token)
        owner_id = token_info["sub"]
        resource_id = await create_resource(
            display_name, f"collection:{location}", owner_id
        )
    else:
        resource_id = uuid4()
        # if we don't have authz configured, we write the collection name mapping to OpenSearch
        await asyncify(create_index_mapping, resource_id, display_name)
    await asyncify(create_collection_index, resource_id)
    print(f"created {location or ''} collection {display_name} with ID {resource_id}")
    return resource_id


async def delete_collection(token, collection_id):
    print(f"deleting collection with ID {collection_id}")
    if auth_enabled:
        authorized = await authorize(token, collection_id, "delete")
        if not authorized:
            raise UnauthorizedOperationError()
        await delete_resource(collection_id)
    else:
        await asyncify(delete_index_mapping, collection_id)
    await asyncify(delete_collection_indices, collection_id)
    print(f"deleted collection with ID {collection_id}")


async def get_documents(token, collection_id):
    if auth_enabled:
        authorized = await authorize(token, collection_id, "read")
        if not authorized:
            raise UnauthorizedOperationError()
    return await asyncify(get_opensearch_documents, collection_id)


async def delete_document(token, collection_id, document_type, document_id):
    if auth_enabled:
        authorized = await authorize(token, collection_id, "delete")
        if not authorized:
            raise UnauthorizedOperationError()
    return await asyncify(
        delete_opensearch_document, collection_id, document_type, document_id
    )


async def get_collection_scopes(token, collection_id):
    if not auth_enabled:
        return {"read", "update", "delete"}
    return set(await list_scopes(token, collection_id))
