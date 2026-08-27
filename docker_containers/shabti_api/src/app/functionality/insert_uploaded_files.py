from fastapi import UploadFile
from .ingesting import insert_document
from .loading import load_file
from shabti_types import UnsupportedFileError, DocumentIngestError, EmptyDocumentError
import zipfile
from io import BytesIO
import os
from keycloak import KeycloakPostError, KeycloakAuthenticationError
from uuid import uuid4
import aiofiles
import aiofiles.os

# for debugging purposes we can set this to True and try to get more information about why an upload is failing
# we make sure this doesn't accidentally get enabled in production
RAISE_EXCEPTIONS = os.getenv("ENVIRONMENT") == "development" and False


async def insert_uploaded_files(
    token: None | str, collection_id, files: list[UploadFile]
):
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
                        yield result
                except Exception as e:
                    await aiofiles.os.remove(
                        os.path.join(os.getenv("SHABTI_FILES_DIR"), file_unique_name)
                    )
                    raise e
            except (KeycloakPostError, KeycloakAuthenticationError) as e:
                raise e
            except UnsupportedFileError as e:
                yield DocumentIngestError(
                    error="UnsupportedFileError", message=e.message, filename=e.filename
                )
            except EmptyDocumentError as e:
                yield DocumentIngestError(
                    error="EmptyDocumentError", message=e.message, filename=e.source
                )
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
                yield DocumentIngestError(
                    error="UnsupportedFileError",
                    message=f"File {file.filename} could not be loaded",
                    filename=file.filename,
                )

    async for x in handle_files(files):
        yield x
