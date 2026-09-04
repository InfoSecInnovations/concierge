import asyncio
import os
import zipfile
from collections.abc import AsyncGenerator

from isi_util.stream_pool import (
    PoolValue,
    StreamPool,
    StreamStoppedError,
)
from keycloak import KeycloakAuthenticationError, KeycloakPostError
from shabti_types import (
    DocumentIngestError,
    DocumentIngestInfo,
    EmptyDocumentError,
    UnsupportedFileError,
    UserInfo,
)

from .ingest_events import IngestEvent, ItemFailed, ItemProgress, ItemQueued
from .ingesting import insert_document
from .loading import load_file
from .save_uploads import SavedUpload, discard, file_path, save_binary
from .settings import setting

# for debugging purposes we can set this to True and try to get more information about why an upload is failing
# we make sure this doesn't accidentally get enabled in production
RAISE_EXCEPTIONS = os.getenv("ENVIRONMENT") == "development" and False


class DocumentLoadError(Exception):
    """A file could not be read at all, as opposed to failing later in the ingest.

    The zip probe below hangs off this rather than off any failure, so an embeddings outage or an
    OpenSearch error part way through a document is no longer mistaken for an archive.
    """


def load_saved(saved: SavedUpload):
    # the handle can be closed here because TikaFileLoader is eager: it reads the whole file, parses
    # the response and builds every page before `insert` asks for the first one
    with open(file_path(saved.item_id), "rb") as f:
        return load_file(f, saved.filename)


def expand_zip(name: str, max_members: int, max_bytes: int) -> list[SavedUpload]:
    """Stream an archive's members out to their own saved files. Call from a thread.

    Members go to disk one at a time rather than into a list of BytesIO holding the whole archive,
    and each becomes an ingest item of its own so they share the pool's limit.
    """
    path = file_path(name)
    if not zipfile.is_zipfile(path):
        return []
    members: list[SavedUpload] = []
    remaining = max_bytes
    with zipfile.ZipFile(path) as archive:
        # zip info includes directories, but we don't want to try to read those!
        entries = [info for info in archive.infolist() if not info.is_dir()]
        if len(entries) > max_members:
            raise ValueError(f"archive holds more than {max_members} files")
        for info in entries:
            with archive.open(info) as source:
                member, written = save_binary(source, remaining)
            remaining -= written
            filename = os.path.basename(info.filename)
            members.append(
                SavedUpload(
                    item_id=member, filename=filename, label=filename or "upload"
                )
            )
    return members


async def insert_uploaded_files(
    actor: UserInfo | None,
    collection_id: str,
    saved: list[SavedUpload],
    pool: StreamPool[DocumentIngestInfo],
) -> AsyncGenerator[IngestEvent, None]:
    """Ingest a batch of already saved uploads, up to the pool's limit at a time.

    Binaries are tracked in `unclaimed` until the document that owns one reports `complete`, and
    whatever is left is deleted on the way out - unsupported, failed, cancelled, never started, or
    an archive whose members now carry the content. That is the same end state as ingesting
    serially, where nothing was written until a file had already loaded.
    """
    unclaimed = {entry.item_id: entry for entry in saved}
    labels = {entry.item_id: entry.label for entry in saved}

    def job(entry: SavedUpload):
        async def factory():
            try:
                # Tika parsing is blocking and takes tens of seconds on a large PDF, which would
                # otherwise stall every other request on the event loop for that whole time
                stream = await asyncio.to_thread(load_saved, entry)
            except Exception as e:
                raise DocumentLoadError(entry.label) from e
            if not stream:
                raise UnsupportedFileError(
                    message="No content was able to be loaded from the file",
                    filename=entry.filename,
                )
            return insert_document(actor, collection_id, stream, entry.item_id)

        return factory

    def failure(item_id: str, error: str, message: str) -> ItemFailed:
        return ItemFailed(
            item_id,
            DocumentIngestError(
                error=error,
                message=message,
                filename=labels.get(item_id),
                label=labels.get(item_id),
            ),
        )

    async def drop(item_id: str) -> None:
        entry = unclaimed.pop(item_id, None)
        if entry is not None:
            await discard(entry.item_id)

    try:
        async with pool:
            for entry in saved:
                pool.submit(job(entry), key=entry.item_id)
            async for result in pool.results():
                if isinstance(result, PoolValue):
                    yield ItemProgress(result.key, result.value)
                    if result.value.complete:
                        # the document owns its binary from here, so it is no longer ours to delete
                        unclaimed.pop(result.key, None)
                    continue
                error = result.error
                if error is None or isinstance(error, StreamStoppedError):
                    # a clean finish claimed its binary above; a stop leaves it to the cleanup below
                    continue
                if isinstance(error, (KeycloakPostError, KeycloakAuthenticationError)):
                    # an auth failure is not this file's problem, so it ends the whole batch:
                    # leaving the loop is what tears the pool down
                    raise error
                if isinstance(error, UnsupportedFileError):
                    yield failure(result.key, "UnsupportedFileError", error.message)
                    await drop(result.key)
                    continue
                if isinstance(error, EmptyDocumentError):
                    yield failure(result.key, "EmptyDocumentError", error.message)
                    await drop(result.key)
                    continue
                members = []
                if isinstance(error, DocumentLoadError) and result.key in unclaimed:
                    try:
                        members = await asyncio.to_thread(
                            expand_zip,
                            result.key,
                            setting("SHABTI_INGEST_MAX_ZIP_MEMBERS"),
                            setting("SHABTI_INGEST_MAX_ZIP_BYTES"),
                        )
                    except Exception:
                        # over a cap, or not an archive after all
                        members = []
                if members:
                    print("Zip file detected, ingesting zip file contents...")
                    # submitted from the reader, which is where submit-while-running is trivially
                    # race free, so members join the same limit as everything else rather than
                    # nesting a second pool inside this one's slot
                    for member in members:
                        unclaimed[member.item_id] = member
                        labels[member.item_id] = member.label
                        pool.submit(job(member), key=member.item_id)
                        yield ItemQueued(member.item_id, member.label)
                    # the archive's own bytes are done with: its members carry the content now
                    await drop(result.key)
                    continue
                if RAISE_EXCEPTIONS:
                    raise error
                yield failure(
                    result.key,
                    "UnsupportedFileError",
                    f"File {labels.get(result.key)} could not be loaded",
                )
                await drop(result.key)
    finally:
        for name in list(unclaimed):
            await discard(name)
