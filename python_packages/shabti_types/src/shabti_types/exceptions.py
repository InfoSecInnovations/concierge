class ShabtiError(Exception):
    def __init__(self, message="", status=400):
        self.message = message
        self.status = status


class CollectionExistsError(ShabtiError):
    def __init__(self, collection_name, message="", location=None):
        super().__init__(message, 409)
        self.collection_name = collection_name
        self.location = location


class InvalidLocationError(ShabtiError):
    def __init__(self, message='location must be "private" or "shared"'):
        super().__init__(message)


class InvalidUserError(ShabtiError):
    def __init__(self, message=""):
        super().__init__(message)


class UnsupportedFileError(Exception):
    def __init__(self, filename, message=""):
        self.message = message
        self.filename = filename


class ModelNotFoundError(ShabtiError):
    def __init__(self, model="", message=""):
        super().__init__(message)
        self.model = model


class EmbeddingsError(ShabtiError):
    def __init__(self, message="", upstream_status=None):
        super().__init__(message, 502)  # upstream LLM failure, not a client error
        self.upstream_status = upstream_status


class EmptyDocumentError(ShabtiError):
    def __init__(self, source="", message=""):
        super().__init__(message)
        self.source = source


class ForbiddenUrlError(ShabtiError):
    def __init__(self, url="", message=""):
        super().__init__(message, 403)
        self.url = url


class CollectionNotFoundError(ShabtiError):
    def __init__(self, collection_id="", message=""):
        super().__init__(message, 404)
        self.collection_id = collection_id


class IngestNotFoundError(ShabtiError):
    def __init__(self, ingest_id="", message=""):
        # 404 for a foreign ingest as well as a missing one, so ids aren't enumerable
        super().__init__(message, 404)
        self.ingest_id = ingest_id


class TooManyIngestsError(ShabtiError):
    def __init__(self, message=""):
        super().__init__(message, 429)
