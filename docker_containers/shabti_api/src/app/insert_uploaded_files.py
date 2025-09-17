from fastapi import UploadFile
from .ingesting import insert_document
from .loading import load_file
from fastapi.responses import StreamingResponse
from shabti_types import UnsupportedFileError
import json
import zipfile
from typing import BinaryIO


async def insert_uploaded_files(
    token: None | str, collection_id, files: list[UploadFile]
):
    def move_ownership(old_file: UploadFile) -> UploadFile:
        new_file = UploadFile(
            file=old_file.file,
            size=old_file.size,
            filename=old_file.filename,
            headers=old_file.headers,
        )
        old_file.file = BinaryIO()
        return new_file

    new_files = [move_ownership(file) for file in files]

    async def response_json():
        for file in new_files:
            if zipfile.is_zipfile(file.file):
                print("TODO: zip file")
                print("TODO: don't treat certain document formats as zip files")
            try:
                doc = load_file(file.file, file.filename)
                if not doc:
                    raise UnsupportedFileError(
                        message="No content was able to be loaded from the file",
                        filename=file.filename,
                    )
                async for result in insert_document(
                    token, collection_id, doc, await file.read()
                ):
                    yield f"{result.model_dump_json(exclude_unset=True)}\n"
            except UnsupportedFileError as e:
                yield f"{json.dumps({'error': 'UnsupportedFileError', 'message': e.message, 'filename': e.filename})}\n"

    return StreamingResponse(response_json())
