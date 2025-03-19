from fastapi.responses import StreamingResponse
from loaders.web import WebLoader
from ingesting import insert_document


async def insert_urls(
    token: str | None, collection_id: str, urls: list[str]
) -> StreamingResponse:
    async def response_json():
        for url in urls:
            doc = WebLoader.load(url)
            if doc:
                async for result in insert_document(token, collection_id, doc):
                    yield result.model_dump_json(exclude_unset=True)

    return StreamingResponse(response_json())
