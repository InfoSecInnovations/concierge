from fastapi.responses import StreamingResponse
from loaders.web import WebLoader
from .ingesting import insert_document


def insert_urls(
    token: str | None, collection_id: str, urls: list[str]
) -> StreamingResponse:
    async def response_json():
        for url in urls:
            doc = WebLoader.load(url)
            if doc:
                async for result in insert_document(token, collection_id, doc):
                    yield f"{result.model_dump_json(exclude_unset=True)}\n"

    return StreamingResponse(response_json())
