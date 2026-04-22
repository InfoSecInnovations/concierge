from fastapi import UploadFile
from .ingesting import insert_document
from .loading import load_file
from fastapi.responses import StreamingResponse
from shabti_types import UnsupportedFileError
import json
import zipfile
from io import BytesIO
import os
from keycloak import KeycloakPostError, KeycloakAuthenticationError
from uuid import uuid4
import aiofiles
import aiofiles.os

# for debugging purposes we can set this to True and try to get more information about why an upload is failing
RAISE_EXCEPTIONS = True


async def insert_uploaded_files(
    token: None | str, collection_id, files: list[UploadFile]
):
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
                    file_unique_name = uuid4().hex
                    async with aiofiles.open(
                        os.path.join(os.getenv("SHABTI_FILES_DIR"), file_unique_name),
                        "wb",
                    ) as f:
                        await file.seek(0)
                        await f.write(await file.read())
                    try:
                        async for result in insert_document(
                            token, collection_id, doc, file_unique_name
                        ):
                            yield f"{result.model_dump_json(exclude_unset=True)}\n"
                    except Exception as e:
                        await aiofiles.os.remove(
                            os.path.join(
                                os.getenv("SHABTI_FILES_DIR"), file_unique_name
                            )
                        )
                        raise e
                except (KeycloakPostError, KeycloakAuthenticationError) as e:
                    raise e
                except UnsupportedFileError as e:
                    yield f"{json.dumps({'error': 'UnsupportedFileError', 'message': e.message, 'filename': e.filename})}\n"
                except Exception as e:
                    if zipfile.is_zipfile(file.file):
                        print("Zip file detected, ingesting zip file contents...")
                        with zipfile.ZipFile(file.file) as my_zip:
                            # for some reason some loaders can't directly process text files from the ZipExtFile type but are fine with BytesIO
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
                    if RAISE_EXCEPTIONS:
                        raise e
                    yield f"{json.dumps({'error': 'UnsupportedFileError', 'message': f'File {file.filename} could not be loaded', 'filename': file.filename})}\n"

        async for x in handle_files(files):
            yield x

    return StreamingResponse(response_json())
