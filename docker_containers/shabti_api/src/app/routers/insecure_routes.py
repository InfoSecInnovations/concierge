from fastapi import APIRouter
from ..functionality.document_collections import (
    create_collection,
    get_collections,
    delete_collection,
)
from shabti_types import (
    BaseCollectionCreateInfo,
    CollectionInfo,
)

router = APIRouter()


@router.post("/collections", response_model_exclude_unset=True, status_code=201)
async def create_collection_route(
    collection_info: BaseCollectionCreateInfo,
) -> CollectionInfo:
    return await create_collection(None, collection_info.collection_name)


@router.get("/collections", response_model_exclude_unset=True)
async def get_collections_route() -> list[CollectionInfo]:
    return await get_collections(None)


@router.delete("/collections/{collection_id}", response_model_exclude_unset=True)
async def delete_collection_route(collection_id: str) -> CollectionInfo:
    return await delete_collection(None, collection_id)
