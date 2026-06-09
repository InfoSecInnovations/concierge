from ..loaders.web import WebLoader
from .ingesting import insert_document


async def insert_urls(token: str | None, collection_id: str, urls: list[str]):
    for url in urls:
        doc = WebLoader.load(url)
        if doc:
            async for result in insert_document(token, collection_id, doc):
                yield result
