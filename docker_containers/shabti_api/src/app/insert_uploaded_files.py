from fastapi import UploadFile
from .ingesting import insert_document
from .loading import load_file
from fastapi.responses import StreamingResponse
from shabti_types import UnsupportedFileError
import json
import zipfile
from typing import BinaryIO
from io import BytesIO
import os


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
        async def handle_files(files: list[UploadFile]):
            for file in files:
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
                except Exception:
                    if zipfile.is_zipfile(file.file):
                        print("Zip file detected, ingesting zip file contents...")
                        with zipfile.ZipFile(file.file) as my_zip:
                            # for some reason the Unstructured loader can't directly process text files from the ZipExtFile type but is fine with BytesIO
                            # zip info includes directories, but we don't want to try to read those!
                            async for x in handle_files(
                                [
                                    UploadFile(
                                        file=BytesIO(my_zip.read(info)),
                                        filename=os.path.basename(info.filename),
                                    )
                                    for info in my_zip.infolist()
                                    if not info.is_dir()
                                ]
                            ):
                                yield x
                        continue
                    yield f"{json.dumps({'error': 'UnsupportedFileError', 'message': f"File {file.filename} could not be loaded", 'filename': file.filename})}\n"

        async for x in handle_files(new_files):
            yield x

    return StreamingResponse(response_json())
