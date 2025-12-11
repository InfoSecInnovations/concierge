from .opensearch import get_client
from fastapi.responses import Response
from urllib.parse import quote


async def serve_binary(collection_id: str, doc_id: str):
    client = get_client()
    item = client.get(id=doc_id, index=collection_id)
    binary = item["_source"]["binary_data"]
    media_type = item["_source"]["media_type"]
    filename = item["_source"]["filename"]
    content_disposition_filename = quote(filename)
    if content_disposition_filename != filename:
        content_disposition = f"inline; filename*=utf-8''{content_disposition_filename}"
    else:
        content_disposition = f'inline; filename="{filename}"'
    return Response(
        bytes.fromhex(binary),
        media_type=media_type,
        headers={"content-disposition": content_disposition},
    )
