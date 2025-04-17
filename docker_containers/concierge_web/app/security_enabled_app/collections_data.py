from pydantic import BaseModel
from concierge_types import AuthzCollectionInfo


class CollectionsData(BaseModel):
    collections: dict[str, AuthzCollectionInfo] = {}
    loading: bool = False
