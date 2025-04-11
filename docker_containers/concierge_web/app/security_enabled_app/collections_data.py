from pydantic import BaseModel
from concierge_types import AuthzCollectionInfo


class CollectionsData(BaseModel):
    collections: list[AuthzCollectionInfo] = []
    loading: bool = False