from .loaders.web import WebLoader
from .ingesting import insert_document


async def insert_urls(
    token: str | None, collection_id: str, urls: list[str], max_depth: int = 1
):
    for url in urls:
        doc = await WebLoader.load(url, max_depth)
        async for result in insert_document(token, collection_id, doc):
            yield result
