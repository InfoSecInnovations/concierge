from ...src.app.functionality.loaders.base_loader import (
    ShabtiDocument,
    collect_pages,
    get_current_time,
    page_list_stream,
)


def metadata():
    return ShabtiDocument.DocumentMetadata(
        source="test",
        ingest_date=get_current_time(),
        media_type="text/plain",
        languages=[],
    )


def page(content: str):
    return ShabtiDocument.ShabtiPage(
        metadata=ShabtiDocument.ShabtiPage.PageMetadata(), content=content
    )


async def test_a_list_backed_stream_knows_its_total_up_front():
    stream = page_list_stream(metadata(), [page("one"), page("two")])
    assert stream.estimated_total() == 2
    seen = [p.content async for p in stream.pages]
    assert seen == ["one", "two"]
    assert stream.estimated_total() == 2


async def test_an_empty_stream_yields_nothing():
    stream = page_list_stream(metadata(), [])
    assert stream.estimated_total() == 0
    assert [p async for p in stream.pages] == []


async def test_collecting_a_stream_rebuilds_the_document():
    stream = page_list_stream(metadata(), [page("one"), page("two")])
    document = await collect_pages(stream)
    assert document.metadata.source == "test"
    assert [p.content for p in document.pages] == ["one", "two"]
