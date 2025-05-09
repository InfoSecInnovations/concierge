from pydantic import BaseModel
from typing import Optional


class UserInfo(BaseModel):
    username: str
    user_id: str


class BaseCollectionCreateInfo(BaseModel):
    collection_name: str


class AuthzCollectionCreateInfo(BaseCollectionCreateInfo):
    location: str
    owner_username: Optional[str] = None


class CollectionInfo(BaseModel):
    collection_name: Optional[str] = None
    collection_id: str


class AuthzCollectionInfo(CollectionInfo):
    location: str
    owner: UserInfo


class DocumentInfo(BaseModel):
    type: str
    source: str
    ingest_date: int
    filename: Optional[str] = None
    media_type: Optional[str] = None
    document_id: str
    page_count: int
    vector_count: int


class DeletedDocumentInfo(BaseModel):
    collection_id: str
    document_id: str
    deleted_element_count: int


class DocumentIngestInfo(BaseModel):
    progress: int
    total: int
    document_id: str
    document_type: str
    label: str


class ModelLoadInfo(BaseModel):
    progress: int
    total: int
    model_name: str


class ModelInfo(BaseModel):
    model_name: str


class PromptInfo(BaseModel):
    collection_id: str
    task: str
    user_input: str
    persona: Optional[str] = None
    enhancers: Optional[list[str]] = None
    file_id: Optional[str] = None


class ServiceStatus(BaseModel):
    running: bool


class PromptConfigInfo(BaseModel):
    prompt: Optional[str] = None


class TaskInfo(PromptConfigInfo):
    greeting: str


class TempFileInfo(BaseModel):
    id: str


class WebFile(BaseModel):
    bytes: bytes
    media_type: str
