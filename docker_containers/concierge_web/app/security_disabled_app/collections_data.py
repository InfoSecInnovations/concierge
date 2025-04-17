from pydantic import BaseModel
from concierge_types import CollectionInfo


class CollectionsData(BaseModel):
    collections: dict[str, CollectionInfo] = {}
    loading: bool = False
