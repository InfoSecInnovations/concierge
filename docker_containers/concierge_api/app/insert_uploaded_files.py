from fastapi import UploadFile
import aiofiles
from .ingesting import insert_document
from .loading import load_file
from fastapi.responses import StreamingResponse


async def insert_uploaded_files(
    token: None | str, collection_id, files: list[UploadFile]
):
    paths = {}
    for file in files:
        async with aiofiles.tempfile.NamedTemporaryFile(
            suffix=file.filename, delete=False
        ) as fp:
            binary = await file.read()
            await fp.write(binary)
            paths[file.filename] = {"path": fp.name, "binary": binary}

    async def response_json():
        for filename, data in paths.items():
            doc = load_file(data["path"], filename)
            if doc:
                async for result in insert_document(
                    token, collection_id, doc, data["binary"]
                ):
                    yield result.model_dump_json(exclude_unset=True)

    return StreamingResponse(response_json())
