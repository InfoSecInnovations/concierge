from fastapi import APIRouter, Depends, UploadFile, HTTPException
from document_collections import (
    get_collections,
    create_collection,
    delete_collection,
    get_documents,
    delete_document,
)
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import StreamingResponse
from typing import Annotated
from authentication import server_url
from models import (
    AuthzCollectionCreateInfo,
    CollectionInfo,
    DocumentInfo,
    DeletedDocumentInfo,
)
from insert_uploaded_files import insert_uploaded_files
from insert_urls import insert_urls
from jwcrypto.jwt import JWTExpired
from authentication import get_keycloak_client

oauth_2_scheme = OAuth2AuthorizationCodeBearer(
    tokenUrl=f"{server_url()}/realms/concierge/protocol/openid-connect/token",
    authorizationUrl=f"{server_url()}/realms/concierge/protocol/openid-connect/auth",
    refreshUrl=f"{server_url()}/realms/concierge/protocol/openid-connect/token",
)


async def valid_access_token(access_token: Annotated[str, Depends(oauth_2_scheme)]):
    try:
        client = get_keycloak_client()
        client.decode_token(access_token)
        return access_token
    except JWTExpired:
        raise HTTPException(status_code=401, detail="Token expired")


router = APIRouter()


@router.get("/collections", response_model_exclude_unset=True)
async def get_collections_route(
    credentials: Annotated[str, Depends(valid_access_token)],
) -> list[CollectionInfo]:
    return await get_collections(credentials)


@router.post("/collections", response_model_exclude_unset=True)
async def create_collection_route(
    collection_info: AuthzCollectionCreateInfo,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> CollectionInfo:
    return await create_collection(
        credentials, collection_info.collection_name, collection_info.location
    )


@router.delete("/collections/{collection_id}", response_model_exclude_unset=True)
async def delete_collection_route(
    collection_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> CollectionInfo:
    return await delete_collection(credentials, collection_id)


@router.get(
    "/collections/{collection_id}/documents",
    response_model_exclude_unset=True,
    response_model=list[DocumentInfo],
)
async def get_documents_route(
    collection_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> list[DocumentInfo]:
    return await get_documents(credentials, collection_id)


@router.post(
    "/collections/{collection_id}/documents/files", response_model_exclude_unset=True
)
async def insert_files_document_route(
    collection_id: str,
    files: list[UploadFile],
    credentials: Annotated[str, Depends(valid_access_token)],
) -> StreamingResponse:
    return await insert_uploaded_files(credentials, collection_id, files)


@router.post(
    "/collections/{collection_id}/documents/urls", response_model_exclude_unset=True
)
async def insert_urls_document_route(
    collection_id: str,
    urls: list[str],
    credentials: Annotated[str, Depends(valid_access_token)],
) -> StreamingResponse:
    return await insert_urls(credentials, collection_id, urls)


@router.delete(
    "/collections/{collection_id}/documents/{document_type}/{document_id}",
    response_model_exclude_unset=True,
)
async def delete_document_route(
    collection_id: str,
    document_type: str,
    document_id: str,
    credentials: Annotated[str, Depends(valid_access_token)],
) -> DeletedDocumentInfo:
    return await delete_document(credentials, collection_id, document_type, document_id)
