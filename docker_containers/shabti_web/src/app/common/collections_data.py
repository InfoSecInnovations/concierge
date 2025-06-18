from pydantic import BaseModel
from shabti_types import CollectionInfo
from typing import TypeVar, Generic

TCollectionInfo = TypeVar("TCollectionInfo", bound=CollectionInfo)


class CollectionsData(BaseModel, Generic[TCollectionInfo]):
    collections: dict[str, TCollectionInfo] = {}
    loading: bool = False
