from fastapi import UploadFile
import aiofiles
from .ingesting import insert_document
from .loading import load_file
from fastapi.responses import StreamingResponse
from shabti_types import UnsupportedFileError
import json


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
            try:
                doc = load_file(data["path"], filename)
                async for result in insert_document(
                    token, collection_id, doc, data["binary"]
                ):
                    yield f"{result.model_dump_json(exclude_unset=True)}\n"
            except UnsupportedFileError as e:
                yield f"{json.dumps({'error': 'UnsupportedFileError', 'message': e.message, 'filename': e.filename})}\n"

    return StreamingResponse(response_json())
