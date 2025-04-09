from pydantic import BaseModel
from concierge_types import CollectionInfo


class CollectionsData(BaseModel):
    collections: list[CollectionInfo] = []
    loading: bool = False