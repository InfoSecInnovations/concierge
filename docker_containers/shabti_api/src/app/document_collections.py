from typing import Literal
from .authorization import (
    authorize,
    create_resource,
    list_resources,
    list_scopes,
    delete_resource,
    UnauthorizedOperationError,
)
from shabti_util import auth_enabled
from shabti_keycloak import get_token_info, get_keycloak_admin_client, get_username
from uuid import uuid4
from .opensearch import (
    create_collection_index,
    delete_collection_indices,
    create_index_mapping,
    delete_index_mapping,
    get_collection_mappings,
    get_collection_mapping,
    get_opensearch_documents,
    delete_opensearch_document,
    get_opensearch_collection_info,
    get_document,
)
from isi_util.async_single import asyncify
from keycloak import KeycloakPostError
from shabti_types import (
    CollectionInfo,
    AuthzCollectionInfo,
    DocumentInfo,
    DeletedDocumentInfo,
    UserInfo,
    CollectionExistsError,
    InvalidLocationError,
    InvalidUserError,
)
from .shabti_logging import log_user_action, log_action, logging_enabled

type Location = Literal["private", "shared"]


async def get_collections(token) -> list[CollectionInfo] | list[AuthzCollectionInfo]:
    if auth_enabled():
        available_resources = await list_resources(token)
        return [
            AuthzCollectionInfo(
                collection_name=resource["displayName"],
                collection_id=resource["_id"],
                location=resource["type"].replace("collection:", ""),
                owner=UserInfo(
                    user_id=resource["attributes"]["shabti_owner"][0],
                    username=get_username(resource["attributes"]["shabti_owner"][0]),
                ),
            )
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
        return [
            CollectionInfo(
                collection_name=mapping["collection_name"],
                collection_id=mapping["collection_id"],
            )
            for mapping in await asyncify(get_collection_mappings)
        ]


async def get_collection_info(collection_id) -> CollectionInfo | AuthzCollectionInfo:
    if auth_enabled():
        admin_client = get_keycloak_admin_client()
        client_id = await admin_client.a_get_client_id("shabti-auth")
        resource = await admin_client.a_get_client_authz_resource(
            client_id=client_id, resource_id=collection_id
        )
        return AuthzCollectionInfo(
            collection_name=resource["displayName"],
            collection_id=resource["_id"],
            location=resource["type"].replace("collection:", ""),
            owner=UserInfo(
                user_id=resource["attributes"]["shabti_owner"][0],
                username=get_username(resource["attributes"]["shabti_owner"][0]),
            ),
        )
    opensearch_info = get_opensearch_collection_info(collection_id)
    return CollectionInfo(
        collection_id=collection_id,
        collection_name=opensearch_info["collection_name"],
    )


# in an unsecured instance collections don't have a location, so None is valid in that case
async def create_collection(
    token,
    display_name: str,
    location: Location | None = None,
    collection_owner: str | None = None,
) -> CollectionInfo | AuthzCollectionInfo:
    print(f"creating {location or ''} collection {display_name}")
    if auth_enabled():
        # when using authz collections should always have a location
        if not location:
            raise InvalidLocationError()
        authorized = await authorize(token, f"collection:{location}:create")
        if not authorized:
            raise UnauthorizedOperationError()
        if collection_owner:
            # only users with the "assign" permission can assign collections to other users
            authorized = await authorize(token, f"collection:{location}:assign")
            if not authorized:
                raise UnauthorizedOperationError()
            admin_client = get_keycloak_admin_client()
            owner_id = await admin_client.a_get_user_id(collection_owner)
            if owner_id is None:
                raise InvalidUserError(
                    f"no user with username {collection_owner} found"
                )
        else:
            token_info = await get_token_info(token)
            owner_id = token_info["sub"]
        try:
            resource_id = await create_resource(
                display_name, f"collection:{location}", owner_id
            )
        except KeycloakPostError as e:
            if e.response_code == 409:
                raise CollectionExistsError(
                    display_name,
                    f"a {location} collection with the name {display_name} already exists",
                )
            else:
                raise e
    else:
        existing = get_collection_mapping(display_name)
        if existing:
            raise CollectionExistsError(
                display_name,
                f"a collection with the name {display_name} already exists",
            )
        resource_id = str(uuid4())
        # if we don't have authz configured, we write the collection name mapping to OpenSearch
        await asyncify(create_index_mapping, resource_id, display_name)
    await asyncify(create_collection_index, resource_id)
    print(f"created {location or ''} collection {display_name} with ID {resource_id}")
    if auth_enabled():
        info = AuthzCollectionInfo(
            collection_name=display_name,
            collection_id=resource_id,
            location=location,
            owner=UserInfo(user_id=owner_id, username=get_username(owner_id)),
        )
        await log_user_action(
            token,
            "CREATE COLLECTION",
            f"Create {location} collection {display_name}",
            collection=info.model_dump(),
        )
        return info
    else:
        info = CollectionInfo(collection_name=display_name, collection_id=resource_id)
        await log_action(
            "CREATE COLLECTION",
            f"Create collection {display_name}",
            collection=info.model_dump(),
        )
        return info


async def delete_collection(token, collection_id):
    print(f"deleting collection with ID {collection_id}")
    info = await get_collection_info(collection_id)
    if auth_enabled():
        authorized = await authorize(token, collection_id, "delete")
        if not authorized:
            raise UnauthorizedOperationError()
        await delete_resource(collection_id)
    else:
        await asyncify(delete_index_mapping, collection_id)
    await asyncify(delete_collection_indices, collection_id)
    print(f"deleted collection with ID {collection_id}")
    if auth_enabled():
        await log_user_action(
            token,
            "DELETE COLLECTION",
            f"Delete collection with ID {collection_id}",
            collection=info.model_dump(),
        )
    else:
        await log_action(
            "DELETE COLLECTION",
            f"Delete collection with ID {collection_id}",
            collection=info.model_dump(),
        )
    return info


def create_document_info(doc):
    return DocumentInfo(
        source=doc["source"],
        ingest_date=doc["ingest_date"],
        vector_count=doc["vector_count"],
        document_id=doc["id"],
        page_count=doc["page_count"],
        media_type=doc["media_type"],
        filename=doc["filename"] if "filename" in doc else None,
        languages=doc["languages"],
    )


async def get_document_info(collection_id, document_id):
    return create_document_info(
        await asyncify(get_document, collection_id, document_id)
    )


async def get_documents(token, collection_id):
    if auth_enabled():
        authorized = await authorize(token, collection_id, "read")
        if not authorized:
            raise UnauthorizedOperationError()
    return [
        create_document_info(doc)
        for doc in await asyncify(get_opensearch_documents, collection_id)
    ]


async def delete_document(token, collection_id, document_id):
    if auth_enabled():
        authorized = await authorize(token, collection_id, "update")
        if not authorized:
            raise UnauthorizedOperationError()
    doc_info = None
    if logging_enabled():
        doc_info = await get_document_info(collection_id, document_id)
    info = DeletedDocumentInfo(
        collection_id=collection_id,
        document_id=document_id,
        deleted_element_count=await asyncify(
            delete_opensearch_document, collection_id, document_id
        ),
    )
    if logging_enabled():
        if auth_enabled():
            await log_user_action(
                token,
                "DELETE DOCUMENT",
                f"Deleted document with ID {document_id} from collection with ID {collection_id}",
                collection=(await get_collection_info(collection_id)).model_dump(),
                document={
                    **doc_info.model_dump(),
                    "deleted_element_count": info.deleted_element_count,
                },
            )
        else:
            await log_action(
                "DELETE DOCUMENT",
                f"Deleted document with ID {document_id} from collection with ID {collection_id}",
                collection=(await get_collection_info(collection_id)).model_dump(),
                document={
                    **doc_info.model_dump(),
                    "deleted_element_count": info.deleted_element_count,
                },
            )
    return info


async def get_collection_scopes(token, collection_id):
    if not auth_enabled():
        return {"read", "update", "delete"}
    return set(await list_scopes(token, collection_id))
