from pydantic import BaseModel
from typing import Optional


class BaseCollectionCreateInfo(BaseModel):
    collection_name: str


class CollectionInfo(BaseModel):
    collection_name: Optional[str] = None
    collection_id: str
    location: Optional[str] = None


class DocumentInfo(BaseModel):
    type: str
    source: str
    ingest_date: int
    filename: str
    media_type: str
    document_id: str
    index: str
    page_count: int
    vector_count: int


class DeletedDocumentInfo(BaseModel):
    collection_id: str
    document_id: str
    document_type: str
    deleted_element_count: int


class DocumentIngestInfo(BaseModel):
    progress: int
    total: int
    document_id: str
    document_type: str
