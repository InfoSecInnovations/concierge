from pydantic import BaseModel
from typing import Optional, Literal


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
    source: str
    ingest_date: int
    filename: Optional[str] = None
    media_type: str
    document_id: str
    page_count: int
    vector_count: int
    languages: list[str]


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


class PageInfo(BaseModel):
    page_number: Optional[int] = None
    source: Optional[str] = None


class PromptSource(BaseModel):
    document_metadata: DocumentInfo
    page_metadata: PageInfo


class PromptChunk(BaseModel):
    response: Optional[str] = None
    source: Optional[PromptSource] = None


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
    content_disposition: str


class DocumentSearchParameters(BaseModel):
    search: Optional[str] = None
    sort: Optional[Literal["relevance", "date_desc", "date_asc"]] = None
    max_results: Optional[int] = None
    filter_document_type: Optional[str] = None
    page: int = 0
