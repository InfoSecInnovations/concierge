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
