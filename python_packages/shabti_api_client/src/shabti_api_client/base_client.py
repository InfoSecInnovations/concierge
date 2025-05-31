from abc import ABC, abstractmethod
from shabti_types import (
    DocumentInfo,
    DocumentIngestInfo,
    TaskInfo,
    PromptConfigInfo,
    ModelLoadInfo,
    WebFile,
)
from typing import Generator, Any


class BaseShabtiClient(ABC):
    @abstractmethod
    async def api_status(self) -> bool:
        pass

    @abstractmethod
    async def delete_collection(self, collection_id: str) -> str:
        pass

    @abstractmethod
    async def get_documents(self, collection_id: str) -> list[DocumentInfo]:
        pass

    @abstractmethod
    async def insert_files(
        self, collection_id: str, file_paths: list[str]
    ) -> Generator[DocumentIngestInfo, Any, None]:
        pass

    @abstractmethod
    async def insert_urls(
        self, collection_id: str, urls: list[str]
    ) -> Generator[DocumentIngestInfo, Any, None]:
        pass

    @abstractmethod
    async def delete_document(self, collection_id, document_id) -> str:
        pass

    @abstractmethod
    async def get_tasks(self) -> dict[str, TaskInfo]:
        pass

    @abstractmethod
    async def get_personas(self) -> dict[str, PromptConfigInfo]:
        pass

    @abstractmethod
    async def get_enhancers(self) -> dict[str, PromptConfigInfo]:
        pass

    @abstractmethod
    async def prompt(
        self,
        collection_id: str,
        prompt: str,
        task: str,
        persona: str | None = None,
        enhancers: list[str] | None = None,
        file_path: str | None = None,
    ) -> Generator[Any, Any, None]:
        pass

    @abstractmethod
    async def ollama_status(self) -> bool:
        pass

    @abstractmethod
    async def opensearch_status(self) -> bool:
        pass

    @abstractmethod
    async def load_model(self, model_name: str) -> Generator[ModelLoadInfo, Any, None]:
        pass

    @abstractmethod
    async def get_file(self, collection_id: str, doc_id: str) -> WebFile:
        pass
