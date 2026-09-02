from .opensearch import get_client
from fastapi.responses import FileResponse
from urllib.parse import quote
import os


async def serve_binary(collection_id: str, doc_id: str):
    client = get_client()
    item = await client.get(id=doc_id, index=collection_id)
    binary_path = os.path.join(
        os.getenv("SHABTI_FILES_DIR"), item["_source"]["binary_path"]
    )
    media_type = item["_source"]["media_type"]
    filename = item["_source"]["filename"]
    content_disposition_filename = quote(filename)
    if content_disposition_filename != filename:
        content_disposition = f"inline; filename*=utf-8''{content_disposition_filename}"
    else:
        content_disposition = f'inline; filename="{filename}"'
    return FileResponse(
        binary_path,
        media_type=media_type,
        headers={"content-disposition": content_disposition},
    )
